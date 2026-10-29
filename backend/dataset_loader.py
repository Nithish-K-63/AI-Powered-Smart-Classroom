"""Dataset Loader and Analytics Module for Smart Classroom AV Assistant.

This module provides reusable, robust utilities to:
1. Load the historical troubleshooting CSV dataset without modifying the original file.
2. Validate schema, types, missing values, duplicates, and label consistency.
3. Generate detailed data-quality reports.
4. Calculate complaint analytics and device-wise statistics dynamically.
5. Prepare symptom-based diagnostic matching and target-leakage-free ML datasets.
6. Enforce strict architectural separation between historical CSV reference data
   and live user complaints stored in MongoDB.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DatasetNotFoundError(FileNotFoundError):
    """Raised when the classroom AV troubleshooting CSV file cannot be located."""

    def __init__(self, checked_paths: List[Path], custom_msg: Optional[str] = None):
        paths_str = "\n  - " + "\n  - ".join(str(p.resolve()) for p in checked_paths)
        msg = custom_msg or (
            f"Classroom AV troubleshooting dataset not found.\n"
            f"Searched candidate locations:{paths_str}\n"
            f"Please ensure 'ai_classroom_av_troubleshooting_5000.csv' is placed inside "
            f"the 'data/' directory or project root."
        )
        super().__init__(msg)
        self.checked_paths = checked_paths


class DatasetValidationError(ValueError):
    """Raised when the dataset fails schema or data-quality validation rules."""

    def __init__(self, issues: List[str]):
        msg = "Dataset validation failed with the following errors:\n" + "\n".join(
            f"  * {issue}" for issue in issues
        )
        super().__init__(msg)
        self.issues = issues


class AVDatasetLoader:
    """Reusable loader, validator, and analytics engine for Classroom AV Data.

    Guarantees:
    - Never mutates the source CSV file on disk.
    - Strictly prevents target leakage when preparing ML features.
    - Decouples historical benchmark records from live MongoDB complaints.
    """

    # Schema definition
    REQUIRED_COLUMNS: List[str] = [
        "room_no",
        "device_type",
        "model",
        "symptom",
        "power_status",
        "input_source",
        "cable_status",
        "fix_step",
        "resolved",
        "escalated",
    ]

    # Pre-diagnostic features (observable BEFORE troubleshooting/resolution)
    PRE_DIAGNOSTIC_FEATURES: List[str] = [
        "room_no",
        "device_type",
        "model",
        "symptom",
        "power_status",
        "input_source",
        "cable_status",
    ]

    # Post-troubleshooting outcome columns (MUST NEVER be used as features when predicting each other)
    POST_OUTCOME_COLUMNS: List[str] = [
        "fix_step",
        "resolved",
        "escalated",
    ]

    # Expected categorical label domains
    EXPECTED_DEVICE_TYPES: set[str] = {"projector", "smart_board", "microphone"}
    EXPECTED_BINARY_LABELS: set[str] = {"yes", "no"}
    EXPECTED_POWER_STATUSES: set[str] = {"on", "off", "standby", "unknown"}
    EXPECTED_CABLE_STATUSES: set[str] = {
        "connected",
        "loose",
        "not applicable",
        "disconnected",
        "unknown",
    }

    def __init__(self, csv_path: Optional[Union[str, Path]] = None):
        """Initialize the loader with an explicit or automatically discovered CSV path."""
        self.csv_path: Path = self._resolve_dataset_path(csv_path)
        self._df: Optional[pd.DataFrame] = None
        logger.info("Initialized AVDatasetLoader targeting: %s", self.csv_path)

    @classmethod
    def _resolve_dataset_path(cls, explicit_path: Optional[Union[str, Path]] = None) -> Path:
        """Resolve the path to the CSV dataset with multi-location discovery and error handling."""
        if explicit_path is not None:
            explicit = Path(explicit_path).resolve()
            if not explicit.is_file():
                raise DatasetNotFoundError(
                    checked_paths=[explicit],
                    custom_msg=f"Explicitly specified CSV dataset not found at: {explicit}",
                )
            return explicit

        candidate_paths: List[Path] = []

        # Check environment variable if configured
        env_path = os.getenv("AV_DATASET_PATH")
        if env_path:
            candidate_paths.append(Path(env_path))

        # Standard project layout paths
        cwd = Path.cwd()
        candidate_paths.extend([
            cwd / "data" / "ai_classroom_av_troubleshooting_5000.csv",
            cwd / "ai_classroom_av_troubleshooting_5000.csv",
        ])

        # Relative to module location (Smart-Classroom-AV-Assistant/backend/..)
        module_root = Path(__file__).resolve().parent.parent
        candidate_paths.extend([
            module_root / "data" / "ai_classroom_av_troubleshooting_5000.csv",
            module_root / "ai_classroom_av_troubleshooting_5000.csv",
        ])

        # Deduplicate while preserving order
        unique_candidates: List[Path] = []
        for p in candidate_paths:
            resolved_p = p.resolve()
            if resolved_p not in unique_candidates:
                unique_candidates.append(resolved_p)

        # Check existence
        for p in unique_candidates:
            if p.is_file():
                return p

        # If none found, raise clear DatasetNotFoundError
        raise DatasetNotFoundError(checked_paths=unique_candidates)

    def load_data(
        self,
        validate: bool = True,
        force_reload: bool = False,
    ) -> pd.DataFrame:
        """Load the dataset into a Pandas DataFrame without modifying the source CSV file.

        Args:
            validate: Whether to run full schema and data-quality checks upon loading.
            force_reload: Force re-reading from disk if already cached in memory.

        Returns:
            A clean copy of the loaded DataFrame.
        """
        if self._df is not None and not force_reload:
            return self._df.copy()

        if not self.csv_path.is_file():
            raise DatasetNotFoundError(
                checked_paths=[self.csv_path],
                custom_msg=f"CSV file missing at configured path: {self.csv_path}",
            )

        logger.info("Reading dataset from: %s", self.csv_path)
        # Read file in read-only mode using pandas
        try:
            df = pd.read_csv(
                self.csv_path,
                dtype=str,  # Read all columns as string first to preserve original tokens
                encoding="utf-8",
                keep_default_na=False,  # Treat empty string explicitly
            )
        except Exception as e:
            raise RuntimeError(f"Failed to read CSV at {self.csv_path}: {e}") from e

        # Normalize string whitespace without altering the original file
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()

        if validate:
            self.validate_dataset(df)

        self._df = df
        logger.info("Successfully loaded %d records and %d columns", len(df), len(df.columns))
        return self._df.copy()

    def validate_dataset(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Validate all columns, data types, missing values, duplicates, and categorical labels.

        Args:
            df: DataFrame to validate; if None, uses self.load_data(validate=False).

        Returns:
            Dictionary containing detailed validation metrics.

        Raises:
            DatasetValidationError: If required columns are missing or fatal invalid labels occur.
        """
        if df is None:
            if self._df is None:
                df = self.load_data(validate=False)
            else:
                df = self._df

        issues: List[str] = []
        warnings: List[str] = []

        # 1. Column Presence Validation
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            issues.append(f"Missing required columns: {missing_cols}")

        unexpected_cols = [col for col in df.columns if col not in self.REQUIRED_COLUMNS]
        if unexpected_cols:
            warnings.append(f"Unexpected extra columns found: {unexpected_cols}")

        if issues:
            raise DatasetValidationError(issues)

        total_rows = len(df)
        if total_rows == 0:
            raise DatasetValidationError(["The dataset contains 0 records."])

        # 2. Missing Values Check (empty strings or NaNs)
        missing_by_col: Dict[str, int] = {}
        for col in self.REQUIRED_COLUMNS:
            empty_count = int((df[col].isna() | (df[col] == "")).sum())
            if empty_count > 0:
                missing_by_col[col] = empty_count
                warnings.append(f"Column '{col}' contains {empty_count} missing/empty values.")

        # 3. Duplicate Rows Check
        duplicate_count = int(df.duplicated().sum())
        if duplicate_count > 0:
            warnings.append(
                f"Dataset contains {duplicate_count} exact duplicate rows "
                f"({duplicate_count / total_rows * 100:.2f}% of data)."
            )

        # 4. Inconsistent Label Validation
        device_types_found = set(df["device_type"].unique())
        invalid_devices = device_types_found - self.EXPECTED_DEVICE_TYPES
        if invalid_devices:
            warnings.append(f"Unrecognized device categories found: {invalid_devices}")

        resolved_labels = set(df["resolved"].unique())
        invalid_resolved = resolved_labels - self.EXPECTED_BINARY_LABELS
        if invalid_resolved:
            issues.append(f"Invalid values in 'resolved' column: {invalid_resolved} (expected yes/no)")

        escalated_labels = set(df["escalated"].unique())
        invalid_escalated = escalated_labels - self.EXPECTED_BINARY_LABELS
        if invalid_escalated:
            issues.append(f"Invalid values in 'escalated' column: {invalid_escalated} (expected yes/no)")

        if issues:
            raise DatasetValidationError(issues)

        validation_result = {
            "status": "PASSED" if not warnings else "PASSED_WITH_WARNINGS",
            "total_records": total_rows,
            "total_columns": len(df.columns),
            "missing_values_by_column": missing_by_col,
            "total_missing_cells": sum(missing_by_col.values()),
            "duplicate_records_count": duplicate_count,
            "duplicate_percentage": round((duplicate_count / total_rows) * 100, 2),
            "warnings": warnings,
            "device_types_detected": sorted(list(device_types_found)),
        }
        return validation_result

    def generate_data_quality_report(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Generate a data-quality audit report showing records, categories, and distributions.

        Returns:
            A structured dictionary representing the data-quality audit.
        """
        if df is None:
            df = self.load_data(validate=True)

        validation = self.validate_dataset(df)
        total_records = len(df)

        # Column schema details
        column_summaries = []
        for col in self.REQUIRED_COLUMNS:
            unique_count = int(df[col].nunique())
            empty_count = int((df[col].isna() | (df[col] == "")).sum())
            column_summaries.append({
                "column": col,
                "dtype": str(df[col].dtype),
                "non_null_count": total_records - empty_count,
                "null_count": empty_count,
                "unique_values_count": unique_count,
                "sample_values": df[col].drop_duplicates().head(3).tolist(),
            })

        # Device categories breakdown
        device_counts = df["device_type"].value_counts().to_dict()
        device_breakdown = {
            dev: {
                "count": int(count),
                "percentage": round((count / total_records) * 100, 2),
            }
            for dev, count in device_counts.items()
        }

        # Target label balance
        resolved_counts = df["resolved"].value_counts().to_dict()
        escalated_counts = df["escalated"].value_counts().to_dict()

        report = {
            "dataset_path": str(self.csv_path),
            "total_records": total_records,
            "total_columns": len(df.columns),
            "memory_usage_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
            "validation_status": validation["status"],
            "data_integrity_score_pct": 100.0 if validation["total_missing_cells"] == 0 else round(
                (1 - (validation["total_missing_cells"] / (total_records * len(self.REQUIRED_COLUMNS)))) * 100, 2
            ),
            "device_categories": device_breakdown,
            "target_distributions": {
                "resolved": resolved_counts,
                "escalated": escalated_counts,
            },
            "duplicates": {
                "count": validation["duplicate_records_count"],
                "percentage": validation["duplicate_percentage"],
            },
            "columns": column_summaries,
            "warnings": validation["warnings"],
        }
        return report

    def get_complaint_analytics(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Compute comprehensive complaint analytics and device-wise statistics dynamically.

        Never hardcodes numbers; all figures reflect actual data in the CSV.
        """
        if df is None:
            df = self.load_data(validate=True)

        total_records = len(df)
        if total_records == 0:
            return {"total_complaints": 0}

        # 1. Device category distribution
        device_counts = df["device_type"].value_counts()
        device_percentages = ((device_counts / total_records) * 100).round(2).to_dict()
        device_counts_dict = device_counts.to_dict()

        # 2. Overall resolution and escalation rates
        resolved_yes = int((df["resolved"] == "yes").sum())
        escalated_yes = int((df["escalated"] == "yes").sum())
        overall_resolution_rate = round((resolved_yes / total_records) * 100, 2)
        overall_escalation_rate = round((escalated_yes / total_records) * 100, 2)

        # 3. Device-wise statistics
        device_stats = {}
        for dev in sorted(df["device_type"].unique()):
            dev_df = df[df["device_type"] == dev]
            dev_total = len(dev_df)
            dev_res = int((dev_df["resolved"] == "yes").sum())
            dev_esc = int((dev_df["escalated"] == "yes").sum())
            device_stats[dev] = {
                "total_complaints": dev_total,
                "share_pct": round((dev_total / total_records) * 100, 2),
                "resolved_count": dev_res,
                "resolution_rate_pct": round((dev_res / dev_total) * 100, 2),
                "escalated_count": dev_esc,
                "escalation_rate_pct": round((dev_esc / dev_total) * 100, 2),
                "unique_models": dev_df["model"].nunique(),
                "top_symptom": dev_df["symptom"].mode()[0] if not dev_df.empty else None,
            }

        # 4. Top symptoms overall
        top_symptoms_series = df["symptom"].value_counts().head(10)
        top_symptoms_overall = [
            {
                "symptom": sym,
                "count": int(cnt),
                "percentage": round((cnt / total_records) * 100, 2),
            }
            for sym, cnt in top_symptoms_series.items()
        ]

        # 5. Top symptoms by device category
        top_symptoms_by_device = {}
        for dev in sorted(df["device_type"].unique()):
            dev_df = df[df["device_type"] == dev]
            syms = dev_df["symptom"].value_counts().head(5)
            top_symptoms_by_device[dev] = [
                {"symptom": s, "count": int(c), "percentage": round((c / len(dev_df)) * 100, 2)}
                for s, c in syms.items()
            ]

        # 6. Environmental status distributions
        cable_dist = df["cable_status"].value_counts().to_dict()
        power_dist = df["power_status"].value_counts().to_dict()
        input_dist = df["input_source"].value_counts().head(8).to_dict()

        return {
            "total_complaints": total_records,
            "overall_metrics": {
                "resolved_count": resolved_yes,
                "resolution_rate_pct": overall_resolution_rate,
                "escalated_count": escalated_yes,
                "escalation_rate_pct": overall_escalation_rate,
            },
            "device_category_counts": device_counts_dict,
            "device_category_percentages": device_percentages,
            "device_wise_statistics": device_stats,
            "top_symptoms_overall": top_symptoms_overall,
            "top_symptoms_by_device": top_symptoms_by_device,
            "cable_status_distribution": cable_dist,
            "power_status_distribution": power_dist,
            "top_input_sources": input_dist,
        }

    def diagnose_symptom(
        self,
        symptom: str,
        device_type: Optional[str] = None,
        model: Optional[str] = None,
        power_status: Optional[str] = None,
        cable_status: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Perform symptom-based diagnostic matching against historical resolutions.

        Retrieves historically proven fix steps, empirical resolution probability,
        and escalation likelihood.
        """
        df = self.load_data(validate=False)

        # Apply search filters
        query_mask = df["symptom"].str.lower() == symptom.lower().strip()
        if device_type:
            query_mask &= df["device_type"].str.lower() == device_type.lower().strip()
        if model:
            query_mask &= df["model"].str.lower() == model.lower().strip()
        if power_status:
            query_mask &= df["power_status"].str.lower() == power_status.lower().strip()
        if cable_status:
            query_mask &= df["cable_status"].str.lower() == cable_status.lower().strip()

        matched_df = df[query_mask]
        matched_count = len(matched_df)

        if matched_count == 0:
            # Fallback to broader symptom search if strict match yielded 0 records
            broad_mask = df["symptom"].str.contains(symptom.strip(), case=False, na=False)
            if device_type:
                broad_mask &= df["device_type"].str.lower() == device_type.lower().strip()
            matched_df = df[broad_mask]
            matched_count = len(matched_df)

        if matched_count == 0:
            return {
                "query": {
                    "symptom": symptom,
                    "device_type": device_type,
                    "model": model,
                },
                "matched_records_count": 0,
                "message": "No historical cases matched this symptom profile.",
                "recommended_fix_steps": [],
            }

        # Analyze historical fix steps
        res_yes = int((matched_df["resolved"] == "yes").sum())
        esc_yes = int((matched_df["escalated"] == "yes").sum())

        fix_groups = matched_df.groupby("fix_step")
        recommended_steps = []
        for step, group in fix_groups:
            step_count = len(group)
            step_res = int((group["resolved"] == "yes").sum())
            step_esc = int((group["escalated"] == "yes").sum())
            recommended_steps.append({
                "fix_step": step,
                "frequency": step_count,
                "frequency_pct": round((step_count / matched_count) * 100, 2),
                "resolution_rate_pct": round((step_res / step_count) * 100, 2),
                "escalation_rate_pct": round((step_esc / step_count) * 100, 2),
            })

        # Rank fix steps primarily by success rate and frequency
        recommended_steps.sort(
            key=lambda x: (x["resolution_rate_pct"], x["frequency"]),
            reverse=True,
        )

        return {
            "query": {
                "symptom": symptom,
                "device_type": device_type,
                "model": model,
                "power_status": power_status,
                "cable_status": cable_status,
            },
            "matched_records_count": matched_count,
            "historical_resolution_rate_pct": round((res_yes / matched_count) * 100, 2),
            "historical_escalation_rate_pct": round((esc_yes / matched_count) * 100, 2),
            "recommended_fix_steps": recommended_steps[:top_k],
        }

    def prepare_ml_features(
        self,
        target_column: str = "escalated",
        feature_columns: Optional[List[str]] = None,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare feature matrix (X) and target vector (y) while strictly PREVENTING TARGET LEAKAGE.

        CRITICAL LEAKAGE RULES ENFORCED:
        1. When predicting 'escalated': 'resolved' and 'fix_step' MUST NOT be in features.
        2. When predicting 'resolved': 'escalated' and 'fix_step' MUST NOT be in features.
        3. When predicting 'fix_step': 'resolved' and 'escalated' MUST NOT be in features.
        Only pre-diagnostic observations (device_type, model, symptom, power_status,
        input_source, cable_status, room_no) are permitted.

        Args:
            target_column: Column to predict ('escalated', 'resolved', or 'fix_step').
            feature_columns: Optional subset of pre-diagnostic features. Defaults to all
                             PRE_DIAGNOSTIC_FEATURES.

        Returns:
            Tuple of (X, y) as Pandas DataFrame and Series.

        Raises:
            ValueError: If target leakage is detected or target is invalid.
        """
        df = self.load_data(validate=True)

        if target_column not in self.POST_OUTCOME_COLUMNS:
            raise ValueError(
                f"Invalid target column '{target_column}'. "
                f"Must be one of {self.POST_OUTCOME_COLUMNS}"
            )

        # Default to safe pre-diagnostic features
        if feature_columns is None:
            features_to_use = list(self.PRE_DIAGNOSTIC_FEATURES)
        else:
            features_to_use = list(feature_columns)

        # STRICT TARGET LEAKAGE CHECK:
        # Detect if any post-outcome columns appear in features
        leaked_columns = [col for col in features_to_use if col in self.POST_OUTCOME_COLUMNS]
        if leaked_columns:
            raise ValueError(
                f"TARGET LEAKAGE DETECTED! The following outcome columns cannot be "
                f"used as input features: {leaked_columns}. "
                f"Permitted pre-diagnostic features: {self.PRE_DIAGNOSTIC_FEATURES}"
            )

        X = df[features_to_use].copy()
        y = df[target_column].copy()

        logger.info(
            "Prepared ML dataset - Target: '%s' | Features: %s | Shape X: %s, Shape y: %s",
            target_column,
            features_to_use,
            X.shape,
            y.shape,
        )
        return X, y

    def train_baseline_classifier(
        self,
        target_column: str = "escalated",
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """Train an optional scikit-learn classification pipeline with zero target leakage.

        Uses OneHotEncoder + RandomForestClassifier with stratified train-test splitting.
        """
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import classification_report, f1_score, precision_score, recall_score
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder

        X, y = self.prepare_ml_features(target_column=target_column)

        # Encode binary target into 0 and 1 if binary
        if target_column in ("escalated", "resolved"):
            y_encoded = (y == "yes").astype(int)
        else:
            y_encoded = y

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y_encoded,
            test_size=test_size,
            random_state=random_state,
            stratify=y_encoded if target_column in ("escalated", "resolved") else None,
        )

        pipeline = Pipeline([
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            (
                "classifier",
                LogisticRegression(
                    max_iter=500,
                    random_state=random_state,
                ),
            ),
        ])

        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        # Evaluation metrics
        metrics = {
            "target": target_column,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "features_used": list(X.columns),
            "target_leakage_prevented": True,
            "classification_report": classification_report(y_test, y_pred, output_dict=True),
        }

        if target_column in ("escalated", "resolved"):
            metrics["accuracy_pct"] = round(float(np.mean(y_test == y_pred)) * 100, 2)
            metrics["precision_pct"] = round(float(precision_score(y_test, y_pred, zero_division=0)) * 100, 2)
            metrics["recall_pct"] = round(float(recall_score(y_test, y_pred, zero_division=0)) * 100, 2)
            metrics["f1_score_pct"] = round(float(f1_score(y_test, y_pred, zero_division=0)) * 100, 2)

        return metrics

    def get_historical_records_for_sync(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Format historical CSV records with metadata separating them from live MongoDB complaints.

        Enforces architectural separation:
        - Historical records are marked `source: "historical_csv"` and `is_historical: True`.
        - Generated records have immutable IDs formatted as `HIST-CSV-XXXXX`.
        - New user complaints are handled by separate collections with `source: "live_mongodb"`.
        """
        df = self.load_data(validate=True)
        if limit:
            df = df.head(limit)

        records: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            record = {
                "record_id": f"HIST-CSV-{idx + 1:05d}",
                "source": "historical_csv",
                "is_historical": True,
                "room_no": row["room_no"],
                "device_type": row["device_type"],
                "model": row["model"],
                "symptom": row["symptom"],
                "power_status": row["power_status"],
                "input_source": row["input_source"],
                "cable_status": row["cable_status"],
                "fix_step": row["fix_step"],
                "resolved": row["resolved"] == "yes",
                "escalated": row["escalated"] == "yes",
            }
            records.append(record)
        return records

    @staticmethod
    def create_live_complaint_record(
        complaint_id: str,
        user_id: str,
        room_no: str,
        device_type: str,
        symptom: str,
        model: Optional[str] = None,
        power_status: str = "unknown",
        input_source: str = "unknown",
        cable_status: str = "unknown",
        notes: str = "",
    ) -> Dict[str, Any]:
        """Schema factory for live user complaints destined for MongoDB.

        Guarantees that live complaints carry distinct attributes:
        `source: 'live_mongodb'`, `is_historical: False`, status lifecycle tracking.
        """
        from datetime import datetime, timezone

        return {
            "complaint_id": complaint_id,
            "source": "live_mongodb",
            "is_historical": False,
            "status": "open",  # Lifecycle: open -> in_progress -> resolved / escalated
            "user_id": user_id,
            "room_no": room_no,
            "device_type": device_type,
            "model": model or "unspecified",
            "symptom": symptom,
            "power_status": power_status,
            "input_source": input_source,
            "cable_status": cable_status,
            "technician_notes": notes,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
            "escalated": False,
        }
