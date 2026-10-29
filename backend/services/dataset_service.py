"""Programmatic Loader & Validator for Public IT Support and FloDial Datasets.

Datasets:
1. benjaminmacklin/IT_Support_V2 (Hugging Face)
2. FloDial (Flowchart-grounded dialogue, IIT Delhi / dair-iitd)

IMPORTANT SAFETY RULES:
- Public datasets are strictly isolated for dialogue pattern analysis, evaluation, and test scenarios.
- They are NEVER blindly inserted into the production campus SOP knowledge base.
- Includes caching, schema inspection, and graceful error handling.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "public_datasets"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class DatasetService:
    """Manages downloading, caching, and inspecting public support datasets."""

    def __init__(self):
        self.it_support_status: Dict[str, Any] = {
            "name": "benjaminmacklin/IT_Support_V2",
            "source": "Hugging Face Datasets Hub",
            "status": "Not Loaded",
            "record_count": 0,
            "sample_records": [],
            "schema_fields": [],
            "error": None,
        }
        self.flodial_status: Dict[str, Any] = {
            "name": "FloDial (Flowchart-Grounded Troubleshooting)",
            "source": "IIT Delhi (GitHub: dair-iitd/FloDial)",
            "license": "Research & Educational Use (Attribution required)",
            "status": "Not Loaded",
            "record_count": 0,
            "sample_flows": [],
            "error": None,
        }

    def load_it_support_dataset(self, max_records: int = 50) -> Dict[str, Any]:
        """Load and normalize benjaminmacklin/IT_Support_V2 from Hugging Face."""
        cache_file = CACHE_DIR / "it_support_v2_cache.json"

        # Check local cache first
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                self.it_support_status.update({
                    "status": "Loaded (Cached)",
                    "record_count": cached_data.get("record_count", 0),
                    "sample_records": cached_data.get("samples", []),
                    "schema_fields": cached_data.get("schema", []),
                    "error": None,
                })
                return self.it_support_status
            except Exception as e:
                logger.warning("Cache read failed: %s. Re-fetching.", e)

        # Attempt downloading via datasets library or direct HF raw API
        try:
            import datasets
            logger.info("Loading benjaminmacklin/IT_Support_V2 via datasets...")
            ds = datasets.load_dataset("benjaminmacklin/IT_Support_V2", split="train", streaming=True)
            samples = []
            schema_keys = set()
            for idx, row in enumerate(ds):
                if idx >= max_records:
                    break
                schema_keys.update(row.keys())
                samples.append({
                    "id": idx + 1,
                    "prompt": str(row.get("instruction") or row.get("prompt") or row.get("question") or row.get("input") or "")[:200],
                    "response": str(row.get("response") or row.get("output") or row.get("answer") or "")[:200],
                })

            cached_data = {
                "record_count": len(samples),
                "schema": sorted(list(schema_keys)),
                "samples": samples[:10],
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cached_data, f, indent=2)

            self.it_support_status.update({
                "status": "Successfully Loaded",
                "record_count": len(samples),
                "sample_records": samples[:10],
                "schema_fields": sorted(list(schema_keys)),
                "error": None,
            })
        except Exception as e:
            logger.warning("Could not download benjaminmacklin/IT_Support_V2: %s", e)
            # Create synthetic representative sample for offline evaluation if network fails
            fallback_samples = [
                {
                    "id": 1,
                    "prompt": "User: Projector power lamp is blinking orange, no display.",
                    "response": "Support: Orange blinking indicates standby or lamp cool-down. Check power source.",
                },
                {
                    "id": 2,
                    "prompt": "User: Wireless microphone emitting loud feedback squeal.",
                    "response": "Support: Reduce amplifier gain and move mic away from front-of-house speakers.",
                },
                {
                    "id": 3,
                    "prompt": "User: Smart Board interactive touch coordinates are offset by 3 inches.",
                    "response": "Support: Run manufacturer calibration utility and orient all 9 target crosshairs.",
                },
            ]
            self.it_support_status.update({
                "status": "Offline Reference Patterns Loaded",
                "record_count": len(fallback_samples),
                "sample_records": fallback_samples,
                "schema_fields": ["id", "prompt", "response"],
                "error": str(e),
            })

        return self.it_support_status

    def load_flodial_dataset(self) -> Dict[str, Any]:
        """Retrieve and inspect FloDial decision-flow structure from GitHub repo."""
        cache_file = CACHE_DIR / "flodial_cache.json"

        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                self.flodial_status.update({
                    "status": "Loaded (Cached)",
                    "record_count": cached.get("record_count", 0),
                    "sample_flows": cached.get("flows", []),
                    "error": None,
                })
                return self.flodial_status
            except Exception:
                pass

        # FloDial RAW GitHub URL
        flodial_url = "https://raw.githubusercontent.com/dair-iitd/FloDial/main/data/test.json"
        try:
            req = urllib.request.Request(
                flodial_url,
                headers={"User-Agent": "SmartClassroomAVAssistant/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                content = response.read().decode("utf-8")
                raw_json = json.loads(content)
                flows = []
                if isinstance(raw_json, list):
                    for idx, item in enumerate(raw_json[:5]):
                        flows.append({
                            "flow_id": idx + 1,
                            "title": item.get("title", item.get("scenario", f"Diagnostic Flow #{idx+1}")),
                            "nodes_count": len(item.get("dialogue", item.get("steps", []))),
                            "sample_step": str(item)[:150],
                        })
                elif isinstance(raw_json, dict):
                    for k, v in list(raw_json.items())[:5]:
                        flows.append({"flow_id": k, "summary": str(v)[:150]})

                self.flodial_status.update({
                    "status": "Successfully Retrieved",
                    "record_count": len(flows),
                    "sample_flows": flows,
                    "error": None,
                })
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump({"record_count": len(flows), "flows": flows}, f, indent=2)

        except Exception as e:
            logger.warning("Could not reach FloDial online repo: %s. Loading local study pattern.", e)
            local_study_flow = [
                {
                    "flow_id": "FLODIAL-AV-01",
                    "title": "Display Power Decision Tree",
                    "steps": [
                        "Check wall master switch -> If OFF, turn ON -> Test",
                        "Check remote power button -> If unresponsive, check AAA batteries",
                        "Check HDMI signal input select -> Match input to connected laptop",
                    ],
                },
                {
                    "flow_id": "FLODIAL-AV-02",
                    "title": "Microphone Audio Signal Diagnostic Tree",
                    "steps": [
                        "Verify transmitter battery level -> Replace AA batteries if LED is red",
                        "Check receiver mute switch -> Ensure unmuted",
                        "Check amplifier master fader -> Raise to 0dB mark",
                    ],
                },
            ]
            self.flodial_status.update({
                "status": "Offline Decision Patterns Loaded",
                "record_count": len(local_study_flow),
                "sample_flows": local_study_flow,
                "error": str(e),
            })

        return self.flodial_status

    def get_status_summary(self) -> Dict[str, Any]:
        """Return combined status of public dataset assets."""
        return {
            "it_support_v2": self.it_support_status,
            "flodial": self.flodial_status,
        }


dataset_service = DatasetService()

