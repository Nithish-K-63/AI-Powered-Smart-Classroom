"""End-to-End Workflow Integration Test for Smart Classroom AV Assistant.

Validates the full complaint-to-resolution and complaint-to-escalation lifecycle:
1. Health and configuration check.
2. Dataset analytics computation.
3. Metadata resolution.
4. AI diagnosis and guided plan generation.
5. Complaint registration.
6. Step-by-step troubleshooting logging and resolution.
7. Escalation ticket creation with technician dispatch.
8. Ticket status update and history tracking.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.api import app


def run_e2e_workflow():
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
            sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
        except Exception:
            pass

    print("=" * 70)
    print("[E2E TEST] STARTING COMPLETE WORKFLOW TEST")
    print("=" * 70)

    client = TestClient(app)

    # 1. Health check
    print("\n[Step 1] Verifying System Health & Storage...")
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health_data = res.json()
    print(f"  [OK] System Health: {health_data['status']}")
    print(f"  [OK] Storage Backend: {health_data['storage']['backend_type']} (Fallback: {health_data['storage']['is_fallback']})")
    print(f"  [OK] Retriever: {health_data['retriever']['backend_used']} with {health_data['retriever']['total_documents_indexed']} documents")

    # 2. Dataset Analytics
    print("\n[Step 2] Verifying Real Dataset Analytics...")
    res = client.get("/api/analytics")
    assert res.status_code == 200
    analytics = res.json()
    assert analytics["total_complaints"] == 5000
    print(f"  [OK] Total Historical Complaints: {analytics['total_complaints']}")
    print(f"  [OK] Overall Resolution Rate: {analytics['overall_metrics']['resolution_rate_pct']}%")
    print(f"  [OK] Device Statistics: {list(analytics['device_wise_statistics'].keys())}")

    # 3. Metadata
    print("\n[Step 3] Fetching Device & Symptom Metadata...")
    res = client.get("/api/metadata")
    assert res.status_code == 200
    meta = res.json()
    assert "projector" in meta["device_types"]
    assert "smart_board" in meta["device_types"]
    assert "microphone" in meta["device_types"]
    print(f"  [OK] Supported Device Categories: {meta['device_types']}")
    print(f"  [OK] Total Classrooms Indexed: {len(meta['rooms'])}")

    # 4. Diagnostic Plan Generation
    print("\n[Step 4] Running AI Diagnosis on 'Board displays no image'...")
    diag_payload = {
        "room_no": "B14",
        "device_type": "smart_board",
        "symptom": "Board displays no image",
        "model": "SMART Board MX265",
        "power_status": "on",
        "input_source": "HDMI 1",
        "cable_status": "connected",
    }
    res = client.post("/api/diagnose", json=diag_payload)
    assert res.status_code == 200
    plan = res.json()
    assert len(plan["troubleshooting_steps"]) > 0
    print(f"  [OK] Historical Resolution Rate: {plan['historical_resolution_rate_pct']}%")
    print(f"  [OK] Escalation Risk Level: {plan['escalation_risk_level']}")
    print(f"  [OK] Generated {len(plan['troubleshooting_steps'])} Step-by-Step Actions:")
    for idx, s in enumerate(plan["troubleshooting_steps"][:3], 1):
        print(f"       Step {idx}: {s[:50]}...")

    # 5. Complaint Registration
    print("\n[Step 5] Registering New Complaint...")
    complaint_payload = {
        "room_no": "B14",
        "device_type": "smart_board",
        "model": "SMART Board MX265",
        "symptom": "Board displays no image",
        "power_status": "on",
        "input_source": "HDMI 1",
        "cable_status": "connected",
        "user_id": "prof_anderson",
        "notes": "Calculus II lecture starting in 10 mins.",
    }
    res = client.post("/api/complaints", json=complaint_payload)
    assert res.status_code == 201
    complaint = res.json()
    complaint_id = complaint["complaint_id"]
    print(f"  [OK] Created Complaint ID: {complaint_id} (Status: {complaint['status']})")

    # 6. Step-by-Step Guided Troubleshooting (Step 1 -> Failed, Step 2 -> Resolved)
    print("\n[Step 6] Simulating Step-by-Step Troubleshooting Execution...")
    # Step 1: fails
    res = client.post(
        f"/api/complaints/{complaint_id}/step",
        json={"step": plan["troubleshooting_steps"][0], "resolved": False},
    )
    assert res.status_code == 200
    updated_c1 = res.json()
    assert updated_c1["status"] == "active"
    assert len(updated_c1["attempted_fixes"]) == 1
    print(f"  [OK] Step 1 Attempt Logged: Unresolved (Complaint remains active)")

    # Step 2: succeeds!
    res = client.post(
        f"/api/complaints/{complaint_id}/step",
        json={"step": plan["troubleshooting_steps"][1], "resolved": True},
    )
    assert res.status_code == 200
    updated_c2 = res.json()
    assert updated_c2["status"] == "resolved"
    assert len(updated_c2["attempted_fixes"]) == 2
    print(f"  [OK] Step 2 Attempt Logged: Resolved! (Complaint status updated to: {updated_c2['status']})")

    # 7. Escalation Ticket Flow (Simulate a second complaint that cannot be resolved)
    print("\n[Step 7] Simulating Complaint Escalation to Field Technician...")
    comp2_payload = {
        "room_no": "A08",
        "device_type": "projector",
        "model": "BenQ MS550",
        "symptom": "Projector will not power on",
        "power_status": "off",
        "input_source": "none",
        "cable_status": "connected",
        "user_id": "dr_patel",
        "notes": "No LED indicators light up at all.",
    }
    res = client.post("/api/complaints", json=comp2_payload)
    assert res.status_code == 201
    comp2 = res.json()
    comp2_id = comp2["complaint_id"]
    print(f"  [OK] Registered Unresolvable Incident: {comp2_id}")

    ticket_payload = {
        "complaint_id": comp2_id,
        "room_no": "A08",
        "device_type": "projector",
        "model": "BenQ MS550",
        "symptom": "Projector will not power on",
        "power_status": "off",
        "input_source": "none",
        "cable_status": "connected",
        "attempted_fixes": [
            {"step": "Check wall socket switch", "resolved": False},
            {"step": "Inspect power cable seating", "resolved": False},
        ],
        "escalation_reason": "No power response after checking supply.",
        "priority": "High",
    }
    res = client.post("/api/tickets", json=ticket_payload)
    assert res.status_code == 201
    ticket = res.json()
    ticket_id = ticket["ticket_id"]
    print(f"  [OK] Created Technician Ticket: {ticket_id} (Priority: {ticket['priority']}, Status: {ticket['status']})")

    # Verify complaint was marked escalated
    res = client.get(f"/api/complaints/{comp2_id}")
    assert res.status_code == 200
    assert res.json()["status"] == "escalated"
    print(f"  [OK] Associated Complaint {comp2_id} transitioned to: 'escalated'")

    # 8. Technician Status Update
    print("\n[Step 8] Updating Ticket by Field Support...")
    res = client.patch(
        f"/api/tickets/{ticket_id}",
        json={
            "status": "In Progress",
            "technician_notes": "Dispatched technician to Room A08 with replacement power brick.",
        },
    )
    assert res.status_code == 200
    updated_t = res.json()
    assert updated_t["status"] == "In Progress"
    assert "replacement power brick" in updated_t["technician_notes"]
    print(f"  [OK] Ticket Updated to: '{updated_t['status']}' | Notes: {updated_t['technician_notes']}")

    # 9. List and Filter Tickets
    print("\n[Step 9] Listing Tickets with Status Filter...")
    res = client.get("/api/tickets?status=In Progress")
    assert res.status_code == 200
    ticket_list = res.json()
    assert any(t["ticket_id"] == ticket_id for t in ticket_list)
    print(f"  [OK] Verified ticket {ticket_id} present in active ticket queue")

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL END-TO-END WORKFLOW INTEGRATION TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_e2e_workflow()
