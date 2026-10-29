"""Comprehensive Test and Verification Script for AVDatasetLoader.

Tests:
1. Safe loading of CSV (5,000 records) without modifying source file.
2. Column schema, data type, null, duplicate, and label validation.
3. Data quality report generation.
4. Actual complaint analytics and device-wise statistics.
5. Symptom-based diagnosis matching.
6. Target leakage prevention enforcement for scikit-learn.
7. Optional scikit-learn model training baseline.
8. Separation of historical records from live MongoDB complaints.
9. Error handling when CSV path is invalid/missing.
"""

import sys
from pathlib import Path
import json

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.dataset_loader import (
    AVDatasetLoader,
    DatasetNotFoundError,
    DatasetValidationError,
)


if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass


def run_all_tests():
    print("=" * 70)
    print("[START] RUNNING SMART CLASSROOM AV DATASET INTEGRATION TESTS")
    print("=" * 70)

    # ---------------------------------------------------------
    # TEST 1: Path Resolution and Safe CSV Loading
    # ---------------------------------------------------------
    print("\n[TEST 1] Testing CSV Path Resolution and Safe Read-Only Loading...")
    loader = AVDatasetLoader()
    df = loader.load_data(validate=True)
    assert df is not None, "Failed to load DataFrame"
    assert len(df) == 5000, f"Expected 5,000 records, got {len(df)}"
    assert len(df.columns) == 10, f"Expected 10 columns, got {len(df.columns)}"
    print(f"  [OK] Successfully read {len(df)} records across {len(df.columns)} columns.")
    print(f"  [OK] Target file path: {loader.csv_path}")

    # ---------------------------------------------------------
    # TEST 2: Schema & Label Validation
    # ---------------------------------------------------------
    print("\n[TEST 2] Testing Schema, Nulls, Duplicates, and Label Validation...")
    val_result = loader.validate_dataset(df)
    assert val_result["status"] in ("PASSED", "PASSED_WITH_WARNINGS")
    assert val_result["total_records"] == 5000
    assert val_result["total_missing_cells"] == 0
    print(f"  [OK] Validation Status: {val_result['status']}")
    print(f"  [OK] Total Missing Cells: {val_result['total_missing_cells']}")
    print(f"  [OK] Duplicates Detected: {val_result['duplicate_records_count']} ({val_result['duplicate_percentage']}%)")
    print(f"  [OK] Device Categories Detected: {val_result['device_types_detected']}")

    # ---------------------------------------------------------
    # TEST 3: Data Quality Report Generation
    # ---------------------------------------------------------
    print("\n[TEST 3] Testing Data Quality Report Generation...")
    dq_report = loader.generate_data_quality_report(df)
    assert dq_report["total_records"] == 5000
    assert "device_categories" in dq_report
    assert "projector" in dq_report["device_categories"]
    assert "smart_board" in dq_report["device_categories"]
    assert "microphone" in dq_report["device_categories"]
    print(f"  [OK] Integrity Score: {dq_report['data_integrity_score_pct']}%")
    print("  [OK] Device Categories Breakdown:")
    for dev, stats in dq_report["device_categories"].items():
        print(f"     - {dev:12s}: {stats['count']:4d} incidents ({stats['percentage']}%)")
    print("  [OK] Target Distributions:")
    print(f"     - Resolved: {dq_report['target_distributions']['resolved']}")
    print(f"     - Escalated: {dq_report['target_distributions']['escalated']}")

    # ---------------------------------------------------------
    # TEST 4: Complaint Analytics & Device-wise Statistics
    # ---------------------------------------------------------
    print("\n[TEST 4] Testing Complaint Analytics & Device-wise Statistics...")
    analytics = loader.get_complaint_analytics(df)
    assert analytics["total_complaints"] == 5000
    overall = analytics["overall_metrics"]
    print(f"  [OK] Total Complaints: {analytics['total_complaints']}")
    print(f"  [OK] Overall Resolution Rate: {overall['resolution_rate_pct']}% ({overall['resolved_count']} resolved)")
    print(f"  [OK] Overall Escalation Rate: {overall['escalation_rate_pct']}% ({overall['escalated_count']} escalated)")
    
    print("\n  [OK] Device-wise Statistics Breakdown:")
    for dev, stats in analytics["device_wise_statistics"].items():
        print(
            f"     - {dev:12s}: Total={stats['total_complaints']:4d} | "
            f"Resolution Rate={stats['resolution_rate_pct']:5.2f}% | "
            f"Escalation Rate={stats['escalation_rate_pct']:5.2f}% | "
            f"Top Symptom='{stats['top_symptom']}'"
        )

    print("\n  [OK] Top 5 Symptoms Overall:")
    for item in analytics["top_symptoms_overall"][:5]:
        print(f"     - {item['symptom']:35s}: {item['count']:4d} incidents ({item['percentage']}%)")

    # ---------------------------------------------------------
    # TEST 5: Symptom-based Diagnosis Matching
    # ---------------------------------------------------------
    print("\n[TEST 5] Testing Symptom-based Diagnosis Engine...")
    test_symptom = "Board displays no image"
    test_device = "smart_board"
    diag = loader.diagnose_symptom(symptom=test_symptom, device_type=test_device)
    assert diag["matched_records_count"] > 0
    print(f"  [OK] Queried Symptom: '{test_symptom}' on '{test_device}'")
    print(f"  [OK] Matched Historical Cases: {diag['matched_records_count']}")
    print(f"  [OK] Historical Resolution Rate: {diag['historical_resolution_rate_pct']}%")
    print(f"  [OK] Recommended Fix Steps:")
    for idx, step in enumerate(diag["recommended_fix_steps"][:3], 1):
        print(
            f"     {idx}. {step['fix_step'][:50]}... "
            f"[Freq: {step['frequency']}, Res: {step['resolution_rate_pct']}%]"
        )

    # ---------------------------------------------------------
    # TEST 6: Strict Target Leakage Prevention
    # ---------------------------------------------------------
    print("\n[TEST 6] Testing Target Leakage Prevention in Feature Preparation...")
    # Attempt intentional target leakage (should raise ValueError)
    try:
        loader.prepare_ml_features(
            target_column="escalated",
            feature_columns=["device_type", "symptom", "resolved"],  # 'resolved' is an outcome!
        )
        assert False, "FAILED: Loader did not block target leakage!"
    except ValueError as e:
        print(f"  [OK] Successfully blocked target leakage: {str(e)[:75]}...")

    # Valid leakage-free feature preparation
    X, y = loader.prepare_ml_features(target_column="escalated")
    assert "resolved" not in X.columns
    assert "escalated" not in X.columns
    assert "fix_step" not in X.columns
    assert len(X) == 5000
    assert len(y) == 5000
    print(f"  [OK] Leakage-free feature matrix verified: {list(X.columns)}")
    print(f"  [OK] Target vector verified: '{y.name}' with {len(y)} samples")

    # ---------------------------------------------------------
    # TEST 7: Scikit-learn Baseline Classification
    # ---------------------------------------------------------
    print("\n[TEST 7] Testing Scikit-learn Baseline Classifier Training...")
    model_results = loader.train_baseline_classifier(target_column="escalated")
    assert model_results["target_leakage_prevented"] is True
    print(f"  [OK] Baseline Classifier Trained (RandomForest + OneHotEncoder)")
    print(f"  [OK] Accuracy: {model_results.get('accuracy_pct')}%")
    print(f"  [OK] Precision: {model_results.get('precision_pct')}%")
    print(f"  [OK] Recall: {model_results.get('recall_pct')}%")
    print(f"  [OK] F1-Score: {model_results.get('f1_score_pct')}%")

    # ---------------------------------------------------------
    # TEST 8: Historical CSV vs Live MongoDB Schema Separation
    # ---------------------------------------------------------
    print("\n[TEST 8] Testing Historical CSV vs Live MongoDB Schema Separation...")
    hist_records = loader.get_historical_records_for_sync(limit=2)
    assert len(hist_records) == 2
    assert hist_records[0]["source"] == "historical_csv"
    assert hist_records[0]["is_historical"] is True
    assert hist_records[0]["record_id"].startswith("HIST-CSV-")
    print(f"  [OK] Historical Record Sample: ID={hist_records[0]['record_id']}, source={hist_records[0]['source']}")

    live_complaint = loader.create_live_complaint_record(
        complaint_id="COMPL-2026-0001",
        user_id="teacher_42",
        room_no="B12",
        device_type="projector",
        symptom="Image flickers",
        notes="Started during period 2",
    )
    assert live_complaint["source"] == "live_mongodb"
    assert live_complaint["is_historical"] is False
    assert live_complaint["status"] == "open"
    print(f"  [OK] Live Complaint Sample: ID={live_complaint['complaint_id']}, source={live_complaint['source']}, status={live_complaint['status']}")

    # ---------------------------------------------------------
    # TEST 9: Error Handling for Missing CSV
    # ---------------------------------------------------------
    print("\n[TEST 9] Testing Error Handling for Missing CSV...")
    try:
        missing_loader = AVDatasetLoader(csv_path="non_existent_folder/bogus_file.csv")
        missing_loader.load_data()
        assert False, "FAILED: Loader did not raise DatasetNotFoundError for missing file!"
    except DatasetNotFoundError as e:
        print(f"  [OK] Successfully raised DatasetNotFoundError with clear diagnostics:")
        print(f"    {str(e).splitlines()[0]}")

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL 9 DATASET INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
