"""FastAPI REST API for Smart Classroom AV Troubleshooting Assistant.

Exposes complete endpoints for:
- Dashboard telemetry & live database metrics
- Authentication & role-based permissions
- Campus infrastructure (blocks, classrooms, QR plaques)
- AI Copilot multi-turn troubleshooting with ChromaDB RAG & Qwen3-8B
- Safety hazard detection & immediate emergency abort
- Technician workspace, service queue & status transitions
- Complaint audit trail & chronological event streams
- Knowledge base management & manual chunk ingestion
- Public IT support datasets (benjaminmacklin/IT_Support_V2 & FloDial)
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Core backend modules
from backend.ai_assistant import assistant
from backend.config import settings
from backend.database.connection import init_database
from backend.database.crud import (
    add_chat_message,
    add_troubleshooting_step,
    assign_technician,
    authenticate_user,
    check_role_permission,
    create_block,
    create_classroom,
    create_complaint,
    create_technician,
    create_user,
    enforce_role_permission,
    find_assigned_technician,
    find_existing_unresolved_complaint,
    get_block_by_id,
    get_chat_messages,
    get_classroom_by_id,
    get_classroom_by_qr_token,
    get_complaint_by_id,
    get_complaint_events,
    get_latest_complaints,
    get_live_metrics,
    get_technician_by_id,
    get_troubleshooting_steps,
    get_user_by_id,
    get_user_by_username,
    list_blocks,
    list_classrooms,
    list_complaints,
    list_knowledge_documents,
    list_notifications,
    list_technicians,
    list_users,
    log_complaint_event,
    record_step_feedback,
    register_knowledge_document,
    update_complaint_status,
)
from backend.dataset_loader import AVDatasetLoader
from backend.knowledge_base import retriever
from backend.model.llm_inference import inference_engine
from backend.nlp.extractor import AVQueryExtractor
from backend.rag.document_processor import ManualDocumentProcessor
from backend.rag.vector_store import vector_store
from backend.repository import repository
from backend.services.complaint_service import complaint_service
from backend.services.dataset_service import dataset_service
from backend.services.notification_service import notification_service
from backend.services.qr_service import qr_service

logger = logging.getLogger(__name__)

# Ensure SQLite tables and schema exist
init_database()

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent AV diagnostics, guided troubleshooting, and technician dispatch for smart classrooms.",
)

# CORS configuration: allow React frontend on any local port (5173, 3000, 8501, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared dataset loader
loader = AVDatasetLoader()


# =====================================================================
# Request / Response Schemas
# =====================================================================
class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class BlockCreateRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = None


class ClassroomCreateRequest(BaseModel):
    block_id: str
    room_number: str
    name: str
    floor: int = 1


class UnifiedComplaintRequest(BaseModel):
    classroom_id: Optional[str] = None
    room_no: Optional[str] = None
    device_type: str
    problem_description: Optional[str] = None
    symptom: Optional[str] = None
    device_model: Optional[str] = "unspecified"
    model: Optional[str] = None
    urgency: Optional[str] = "Normal"
    reporter_user_id: Optional[str] = None
    user_id: Optional[str] = None
    power_status: Optional[str] = "unknown"
    input_source: Optional[str] = "unknown"
    cable_status: Optional[str] = "unknown"
    notes: Optional[str] = None


class DiagnoseRequest(BaseModel):
    room_no: str = Field(..., example="E15")
    device_type: str = Field(..., example="smart_board")
    symptom: str = Field(..., example="Board displays no image")
    model: Optional[str] = Field(None, example="SMART Board MX265")
    power_status: str = Field("unknown", example="on")
    input_source: str = Field("unknown", example="HDMI 1")
    cable_status: str = Field("unknown", example="connected")


class StepAttemptRequest(BaseModel):
    step: str
    resolved: bool


class TicketCreateRequest(BaseModel):
    complaint_id: Optional[str] = None
    room_no: str
    device_type: str
    symptom: str
    model: Optional[str] = "unspecified"
    power_status: str = "unknown"
    input_source: str = "unknown"
    cable_status: str = "unknown"
    attempted_fixes: List[Dict[str, Any]] = []
    escalation_reason: str = "Troubleshooting steps failed to resolve issue."
    priority: str = "High"


class TicketUpdateRequest(BaseModel):
    status: Optional[str] = None
    technician_notes: Optional[str] = None


class StatusUpdateRequest(BaseModel):
    status: str
    actor_name: str
    actor_role: str
    resolution_notes: Optional[str] = None
    resolved_by_user_id: Optional[str] = None


class ChatTroubleshootRequest(BaseModel):
    complaint_id: Optional[str] = None
    classroom_id: Optional[str] = None
    block_id: Optional[str] = None
    room_label: Optional[str] = "S-204"
    device_type: str = "projector"
    device_model: Optional[str] = "unspecified"
    urgency: str = "Normal"
    user_message: str
    step_number: int = 1


class StepFeedbackRequest(BaseModel):
    step_number: int
    feedback: str  # "worked", "failed", "skipped"


class EscalateRequest(BaseModel):
    complaint_id: str
    reason: Optional[str] = "Requested technician escalation."
    send_phone_call: bool = False
    confirmed_by_user: bool = False


# =====================================================================
# System Health & Telemetry
# =====================================================================
@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    """Return health status, storage status, and LLM model status."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": repository.get_storage_status(),
        "retriever": retriever.get_status(),
        "llm_engine": inference_engine.get_status(),
        "vector_store_chunks": vector_store.count(),
        "database": "SQLite (WAL Mode, 11 Tables)",
    }


# =====================================================================
# Dashboard Telemetry & Metrics (Live Database Queries)
# =====================================================================
@app.get("/api/dashboard/metrics")
def get_dashboard_metrics() -> Dict[str, Any]:
    """Return live metrics, weekly trends, device distribution, and latest complaints."""
    metrics = get_live_metrics()
    total = metrics["total_complaints"]
    resolved = metrics["resolved_complaints"]
    pending = metrics["pending_complaints"] + metrics.get("in_progress_complaints", 0)
    escalated = metrics["escalated_complaints"]
    resolution_rate = round((resolved / total * 100), 1) if total > 0 else 0.0

    # Device breakdown
    dist = metrics.get("device_distribution", {})
    device_distribution = [
        {"name": "Projector", "count": dist.get("projector", 0), "key": "projector"},
        {"name": "Microphone", "count": dist.get("microphone", 0), "key": "microphone"},
        {"name": "Smart board", "count": dist.get("smart_board", 0), "key": "smart_board"},
        {"name": "Speaker", "count": dist.get("speaker", 0), "key": "speaker"},
        {"name": "Display", "count": dist.get("display", 0), "key": "display"},
    ]

    # Weekly trend bars dynamically computed from live SQLite complaints
    dow_counts = {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0}
    dow_map = {"0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat"}
    from backend.database.connection import db_session
    with db_session() as conn:
        cursor = conn.execute(
            "SELECT strftime('%w', created_at) AS dow, COUNT(*) AS count FROM complaints GROUP BY dow"
        )
        for row in cursor.fetchall():
            d_name = dow_map.get(str(row["dow"]))
            if d_name:
                dow_counts[d_name] = row["count"]

    trend = [{"day": d, "value": dow_counts[d]} for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]]

    # Latest 5 complaints for the floating quick-view panel
    latest = get_latest_complaints(limit=5)

    return {
        "total_complaints": total,
        "resolved_complaints": resolved,
        "pending_complaints": pending,
        "escalated_complaints": escalated,
        "resolution_rate_percent": resolution_rate,
        "device_distribution": device_distribution,
        "weekly_trend": trend,
        "latest_complaints": latest,
    }


# =====================================================================
# Authentication & Users
# =====================================================================
@app.post("/api/auth/login")
def login(req: LoginRequest) -> Dict[str, Any]:
    """Authenticate user with username or email and verified salted password hash."""
    user = authenticate_user(req.username_or_email, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials.",
        )
    parts = user["full_name"].split()
    initials = "".join([p[0] for p in parts][:2]).upper() if parts else "CA"
    role_map = {"admin": "Administrator", "teacher": "Teacher", "technician": "Technician"}
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "email": user["email"],
        "role": role_map.get(user["role"].lower(), "Administrator"),
        "role_raw": user["role"].lower(),
        "department": user.get("department", "Campus AV Operations"),
        "initials": initials,
    }


@app.get("/api/auth/users")
def get_users(role: Optional[str] = None) -> List[Dict[str, Any]]:
    """List registered users."""
    return list_users(role=role)


# =====================================================================
# Campus Infrastructure (Blocks & Classrooms)
# =====================================================================
@app.get("/api/blocks")
def get_blocks() -> List[Dict[str, Any]]:
    """List all campus blocks."""
    return list_blocks()


@app.post("/api/blocks", status_code=status.HTTP_201_CREATED)
def add_block(req: BlockCreateRequest) -> Dict[str, Any]:
    """Create a new campus block."""
    return create_block(code=req.code, name=req.name, description=req.description)


@app.get("/api/classrooms")
def get_classrooms(block_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List classrooms with block codes and QR tokens."""
    return list_classrooms(block_id=block_id)


@app.post("/api/classrooms", status_code=status.HTTP_201_CREATED)
def add_classroom(req: ClassroomCreateRequest) -> Dict[str, Any]:
    """Create a new classroom with auto-generated opaque QR token."""
    return create_classroom(
        block_id=req.block_id,
        room_number=req.room_number,
        name=req.name,
        floor=req.floor,
    )


@app.get("/api/classrooms/{classroom_id}")
def get_classroom(classroom_id: str) -> Dict[str, Any]:
    """Get single classroom by ID."""
    room = get_classroom_by_id(classroom_id)
    if not room:
        raise HTTPException(status_code=404, detail="Classroom not found")
    return room


@app.get("/api/classrooms/token/{qr_token}")
def resolve_classroom_by_token(qr_token: str) -> Dict[str, Any]:
    """Resolve classroom details from opaque QR token."""
    room = get_classroom_by_qr_token(qr_token)
    if not room:
        raise HTTPException(status_code=404, detail="Classroom QR token not found.")
    return room


@app.get("/api/classrooms/{classroom_id}/qr-plaque")
def get_classroom_qr_plaque(classroom_id: str) -> Dict[str, Any]:
    """Generate printable base64 QR plaque for classroom."""
    room = get_classroom_by_id(classroom_id)
    if not room:
        raise HTTPException(status_code=404, detail="Classroom not found")
    qr_b64 = qr_service.generate_qr_base64(room["id"], room["qr_code_token"])
    return {
        "classroom": room,
        "qr_base64": qr_b64,
        "token": room["qr_code_token"],
    }


# =====================================================================
# Technicians
# =====================================================================
@app.get("/api/technicians")
def get_technicians() -> List[Dict[str, Any]]:
    """List all campus AV technicians."""
    return list_technicians()


# =====================================================================
# AI Diagnostics & Guided Troubleshooting (Legacy & Assistant Engine)
# =====================================================================
@app.post("/api/diagnose")
def diagnose_issue(req: DiagnoseRequest) -> Dict[str, Any]:
    """Analyze symptoms and generate a guided troubleshooting plan with RAG context."""
    try:
        plan = assistant.analyze_and_plan(
            device_type=req.device_type,
            symptom=req.symptom,
            room_no=req.room_no,
            model=req.model,
            power_status=req.power_status,
            input_source=req.input_source,
            cable_status=req.cable_status,
        )
        return plan
    except Exception as e:
        logger.error("Error during diagnosis: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Complaints Management
# =====================================================================
@app.get("/api/complaints")
def get_complaints(
    status: Optional[str] = Query(None),
    block_id: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    technician_id: Optional[str] = Query(None),
    room_no: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """List and filter complaints from SQLite database and repository."""
    results = list_complaints(
        status=status,
        block_id=block_id,
        device_type=device_type,
        technician_id=technician_id,
        search=search,
        limit=limit,
    )
    if not results and (room_no or status):
        # Fall back to repository for test_workflow / json store
        return repository.list_complaints(
            device_type=device_type,
            room_no=room_no,
            status=status,
            limit=limit,
        )
    return results


@app.post("/api/complaints", status_code=status.HTTP_201_CREATED)
def submit_complaint(req: UnifiedComplaintRequest) -> Dict[str, Any]:
    """Submit a new classroom AV complaint (supports both React frontend & legacy test requests)."""
    room_number = req.room_no or "Room"
    dev_type = req.device_type.lower().replace(" ", "_")
    desc = req.problem_description or req.symptom or "AV issue"
    dev_model = req.device_model if req.device_model != "unspecified" else (req.model or "unspecified")
    user_id = req.reporter_user_id or req.user_id or "teacher1"
    urgency = req.urgency or "Normal"

    complaint_id = f"CMP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    legacy_record = {
        "complaint_id": complaint_id,
        "room_no": room_number,
        "device_type": dev_type,
        "symptom": desc,
        "model": dev_model,
        "power_status": req.power_status or "unknown",
        "input_source": req.input_source or "unknown",
        "cable_status": req.cable_status or "unknown",
        "user_id": user_id,
        "notes": req.notes or "",
        "status": "active",
        "attempted_fixes": [],
    }
    repo_complaint = repository.create_complaint(legacy_record)

    # Find classroom in SQLite
    cls_id = req.classroom_id
    if not cls_id and req.room_no:
        all_rooms = list_classrooms()
        for r in all_rooms:
            if r["room_number"].lower() == req.room_no.lower():
                cls_id = r["id"]
                break
        if not cls_id and all_rooms:
            cls_id = all_rooms[0]["id"]

    if cls_id:
        try:
            sqlite_comp = create_complaint(
                classroom_id=cls_id,
                device_type=dev_type,
                problem_description=desc,
                device_model=dev_model,
                urgency=urgency,
                reporter_user_id=user_id,
            )
            sqlite_comp["complaint_id"] = complaint_id
            sqlite_copy = dict(legacy_record)
            sqlite_copy["complaint_id"] = sqlite_comp["id"]
            sqlite_copy["status"] = "active"
            repository.create_complaint(sqlite_copy)
            # If called with legacy schema, ensure both fields match
            if req.symptom or req.room_no:
                repo_complaint["status"] = "active"
                return repo_complaint
            return sqlite_comp
        except Exception as e:
            logger.warning("Error creating SQLite complaint: %s", e)

    return repo_complaint


@app.get("/api/complaints/{complaint_id}")
def get_single_complaint(complaint_id: str) -> Dict[str, Any]:
    """Retrieve full complaint details with classroom and technician info."""
    comp = get_complaint_by_id(complaint_id)
    if not comp:
        comp = repository.get_complaint(complaint_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if "complaint_id" not in comp:
        comp["complaint_id"] = comp.get("id")
    return comp


@app.post("/api/complaints/{complaint_id}/step")
def record_troubleshooting_step(
    complaint_id: str,
    req: StepAttemptRequest,
) -> Dict[str, Any]:
    """Log an attempted guided troubleshooting step and update resolution status."""
    updated = repository.add_attempted_fix(
        complaint_id=complaint_id,
        fix_step=req.step,
        resolved=req.resolved,
    )
    if not updated:
        # Check if complaint exists in SQLite
        sq = get_complaint_by_id(complaint_id)
        if sq:
            add_troubleshooting_step(
                complaint_id=complaint_id,
                step_number=1,
                instruction=req.step,
                status="fixed" if req.resolved else "failed",
                user_feedback="success" if req.resolved else "failed",
            )
            if req.resolved:
                update_complaint_status(complaint_id, "resolved", "User", "teacher", "Resolved via guided step.")
            return get_complaint_by_id(complaint_id) # type: ignore
        raise HTTPException(status_code=404, detail="Complaint not found")
    return updated


# =====================================================================
# Technician Escalation Tickets Endpoints
# =====================================================================
@app.post("/api/tickets", status_code=status.HTTP_201_CREATED)
def create_escalation_ticket(req: TicketCreateRequest) -> Dict[str, Any]:
    """Create a formal technician escalation ticket for unresolved issues."""
    ticket_id = f"TCK-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    ticket_data = {
        "ticket_id": ticket_id,
        "complaint_id": req.complaint_id,
        "room_no": req.room_no,
        "device_type": req.device_type,
        "model": req.model,
        "symptom": req.symptom,
        "power_status": req.power_status,
        "input_source": req.input_source,
        "cable_status": req.cable_status,
        "attempted_fixes": req.attempted_fixes,
        "escalation_reason": req.escalation_reason,
        "priority": req.priority,
        "status": "Pending Technician",
        "technician_notes": "",
    }
    created = repository.create_ticket(ticket_data)
    if req.complaint_id:
        try:
            update_complaint_status(
                complaint_id=req.complaint_id,
                status="escalated",
                actor_name="Automated Ticket Dispatcher",
                actor_role="system",
                resolution_notes=f"Escalation ticket {ticket_id} created: {req.escalation_reason}",
            )
        except Exception:
            pass
    return created


@app.get("/api/tickets")
def list_tickets(
    status: Optional[str] = Query(None),
    device_type: Optional[str] = Query(None),
    room_no: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    """List escalation tickets."""
    return repository.list_tickets(
        status=status,
        device_type=device_type,
        room_no=room_no,
        limit=limit,
    )


@app.patch("/api/tickets/{ticket_id}")
def update_ticket_status(
    ticket_id: str,
    req: TicketUpdateRequest,
) -> Dict[str, Any]:
    """Update status or technician notes on a ticket."""
    updates = {}
    if req.status is not None:
        updates["status"] = req.status
    if req.technician_notes is not None:
        updates["technician_notes"] = req.technician_notes

    updated = repository.update_ticket(ticket_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated


@app.post("/api/complaints/{complaint_id}/status")
def change_complaint_status(complaint_id: str, req: StatusUpdateRequest) -> Dict[str, Any]:
    """Update complaint status (acknowledge, diagnostic note, resolve)."""
    try:
        updated = update_complaint_status(
            complaint_id=complaint_id,
            status=req.status,
            actor_name=req.actor_name,
            actor_role=req.actor_role,
            resolution_notes=req.resolution_notes,
            resolved_by_user_id=req.resolved_by_user_id,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Complaint not found")
        return updated
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/complaints/{complaint_id}/escalate")
def escalate_complaint(complaint_id: str, req: EscalateRequest) -> Dict[str, Any]:
    """Escalate complaint to assigned technician with in-app notification and optional Twilio call."""
    cid = req.complaint_id or complaint_id
    res = complaint_service.escalate_to_technician(
        complaint_id=cid,
        escalation_reason=req.reason or "Escalated to technician.",
        dispatch_voice_call=req.send_phone_call,
        confirmed_by_user=req.confirmed_by_user,
    )
    return res


@app.get("/api/duplicate-check")
def check_duplicate(classroom_id: str, device_type: str) -> Dict[str, Any]:
    """Check if an unresolved complaint already exists for this room and device."""
    existing = find_existing_unresolved_complaint(classroom_id, device_type.lower().replace(" ", "_"))
    return {
        "has_duplicate": existing is not None,
        "complaint": existing,
    }


# =====================================================================
# AI Troubleshooting Chat (ChromaDB RAG + Qwen3-8B)
# =====================================================================
@app.post("/api/chat/troubleshoot")
def chat_troubleshoot(req: ChatTroubleshootRequest) -> Dict[str, Any]:
    """Perform grounded multi-turn AI troubleshooting step."""
    cid = req.complaint_id
    dev_cat = req.device_type.lower().replace(" ", "_")

    # If no complaint ID yet, initiate new session in SQLite
    if not cid:
        res = complaint_service.initiate_troubleshooting_session(
            classroom_id=req.classroom_id,
            problem_description=req.user_message,
            device_type=dev_cat,
            device_model=req.device_model,
            urgency=req.urgency,
        )
        return {
            "complaint_id": res["complaint"]["id"],
            "complaint": res["complaint"],
            "ai_response": res["ai_response"],
            "retrieved_sources": res.get("retrieved_evidence", []),
            "is_safety_hazard": res["ai_response"].get("is_safety_hazard", False),
        }

    complaint_rec = get_complaint_by_id(cid)
    # Store incoming teacher message
    add_chat_message(cid, "user", req.user_message)

    # 1. NLP Safety Hazard Check (smoke, sparks, burning smells, exposed wiring)
    hazard = AVQueryExtractor.detect_safety_hazard(req.user_message)

    # 2. ChromaDB Evidence Retrieval
    retrieved_evidence = []
    if not hazard:
        retrieved_evidence = vector_store.query(
            query_text=req.user_message,
            equipment_category=dev_cat,
            top_k=2,
        )

    # 3. Qwen3-8B Inference (OpenAI-compatible endpoint or grounded synthesis)
    ai_response = inference_engine.generate_troubleshooting_response(
        device_type=dev_cat,
        user_problem=req.user_message,
        classroom_context={},
        retrieved_evidence=retrieved_evidence,
        conversation_history=[],
        step_number=req.step_number,
        is_safety_hazard=bool(hazard),
        hazard_details=hazard,
    )

    # 4. Store Assistant response & citations in SQLite
    add_chat_message(
        complaint_id=cid,
        sender_role="assistant",
        message_text=ai_response["troubleshooting_instruction"],
        retrieved_sources=retrieved_evidence,
    )

    # 5. If safety hazard, automatically escalate complaint
    if ai_response.get("is_safety_hazard"):
        complaint_service.escalate_to_technician(cid, f"EMERGENCY SAFETY HAZARD: {hazard}")

    return {
        "complaint_id": cid,
        "complaint": get_complaint_by_id(cid),
        "ai_response": ai_response,
        "retrieved_sources": retrieved_evidence,
        "is_safety_hazard": ai_response.get("is_safety_hazard", False),
    }


@app.get("/api/chat/{complaint_id}")
def get_chat_history(complaint_id: str) -> List[Dict[str, Any]]:
    """Retrieve persistent conversation history from SQLite."""
    return get_chat_messages(complaint_id)


@app.post("/api/chat/{complaint_id}/feedback")
def submit_step_feedback(complaint_id: str, req: StepFeedbackRequest) -> Dict[str, Any]:
    """Process feedback on a troubleshooting step."""
    return complaint_service.process_step_feedback_and_next(
        complaint_id=complaint_id,
        step_number=req.step_number,
        feedback=req.feedback,
    )


# =====================================================================
# Audit Timeline & Event Stream
# =====================================================================
@app.get("/api/complaints/{complaint_id}/events")
def get_complaint_audit_trail(complaint_id: str) -> List[Dict[str, Any]]:
    """Retrieve immutable chronological audit events for a complaint."""
    return get_complaint_events(complaint_id)


# =====================================================================
# Knowledge Base & Manual Ingestion
# =====================================================================
@app.get("/api/knowledge-base/documents")
def get_knowledge_documents() -> List[Dict[str, Any]]:
    """List all approved SOP manuals registered in knowledge base."""
    return list_knowledge_documents()


@app.post("/api/knowledge-base/upload", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_manual(
    title: str = Query(...),
    equipment_category: str = Query(...),
    uploaded_by: str = Query("campus_admin"),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """Upload PDF, TXT, or MD manual, chunk it, and index into ChromaDB vector store."""
    manuals_dir = Path(__file__).resolve().parent.parent / "data" / "campus_manuals"
    manuals_dir.mkdir(parents=True, exist_ok=True)
    dest_path = manuals_dir / file.filename

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    processor = ManualDocumentProcessor(chunk_size=400, chunk_overlap=60)
    doc_rec = register_knowledge_document(
        title=title,
        filename=file.filename,
        file_type=dest_path.suffix.lstrip("."),
        file_path=str(dest_path),
        total_chunks=0,
        uploaded_by=uploaded_by,
        metadata={"equipment_category": equipment_category},
    )

    chunks = processor.process_file(
        file_path=dest_path,
        doc_id=doc_rec["id"],
        title=title,
        equipment_category=equipment_category,
    )
    vector_store.add_chunks(chunks)

    return {
        "success": True,
        "document": doc_rec,
        "chunks_indexed": len(chunks),
        "total_store_count": vector_store.count(),
    }


# =====================================================================
# Public IT Support Datasets
# =====================================================================
@app.get("/api/datasets/status")
def get_dataset_statuses() -> Dict[str, Any]:
    """Return status of public dialog datasets (IT_Support_V2 & FloDial)."""
    return {
        "it_support_v2": dataset_service.it_support_status,
        "flodial": dataset_service.flodial_status,
    }


@app.post("/api/datasets/verify")
def verify_public_datasets() -> Dict[str, Any]:
    """Verify or reload public support datasets."""
    d1 = dataset_service.load_it_support_dataset()
    d2 = dataset_service.load_flodial_dataset()
    return {
        "it_support_v2": d1,
        "flodial": d2,
    }


# =====================================================================
# Dataset Analytics & Diagnostics (Legacy Compatibility)
# =====================================================================
@app.get("/api/analytics")
def get_dataset_analytics() -> Dict[str, Any]:
    """Return dataset analytics."""
    return loader.get_complaint_analytics()


@app.get("/api/data-quality")
def get_data_quality_report() -> Dict[str, Any]:
    """Return data-quality audit report."""
    return loader.generate_data_quality_report()


@app.get("/api/metadata")
def get_metadata() -> Dict[str, Any]:
    """Return metadata for devices and symptoms."""
    df = loader.load_data(validate=False)
    devices = sorted(df["device_type"].unique().tolist())
    return {
        "device_types": devices,
        "models_by_device": {d: sorted(df[df["device_type"] == d]["model"].unique().tolist()) for d in devices},
        "symptoms_by_device": {d: sorted(df[df["device_type"] == d]["symptom"].unique().tolist()) for d in devices},
        "rooms": sorted(df["room_no"].unique().tolist()),
    }
