"""Database CRUD operations for Smart Classroom AV Assistant.

Uses parameterized queries, explicit transactions, and returns dictionaries or objects.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .connection import db_session, init_database

DEMO_SALT = "campusav_secure_salt_2026"

ROLE_PERMISSIONS: Dict[str, set[str]] = {
    "admin": {
        "view_dashboard", "chat", "scan_qr", "raise_request",
        "technician_workspace", "complaint_logs", "knowledge_base",
        "admin_settings", "manage_infrastructure", "manage_users",
        "upload_manuals", "resolve_complaint", "acknowledge_complaint",
        "add_diagnostic_note",
    },
    "teacher": {
        "view_dashboard", "chat", "scan_qr", "raise_request",
        "complaint_logs",
    },
    "technician": {
        "view_dashboard", "scan_qr", "raise_request",
        "technician_workspace", "complaint_logs", "acknowledge_complaint",
        "add_diagnostic_note", "resolve_complaint",
    },
}


def hash_password(raw_password: str) -> str:
    """Hash raw password with persistent campus salt using SHA-256."""
    return hashlib.sha256(f"{DEMO_SALT}{raw_password}".encode("utf-8")).hexdigest()


def verify_password(raw_password: str, stored_hash: Optional[str]) -> bool:
    """Verify raw password against stored salted hash."""
    if not stored_hash:
        return False
    return hash_password(raw_password) == stored_hash


def check_role_permission(role: str, action: str) -> bool:
    """Check if given role has permission to execute action."""
    normalized_role = (role or "").strip().lower()
    return action in ROLE_PERMISSIONS.get(normalized_role, set())


def enforce_role_permission(role: str, action: str) -> None:
    """Raise PermissionError if role is not authorized for action."""
    if not check_role_permission(role, action):
        raise PermissionError(f"Role '{role}' is not authorized to perform action '{action}'.")


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# =====================================================================
# Users & Roles
# =====================================================================
def create_user(
    username: str,
    full_name: str,
    email: str,
    role: str,
    department: Optional[str] = None,
    password: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new user record with secure password hashing."""
    user_id = f"USR-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now_iso()
    pw_hash = hash_password(password) if password else hash_password("Default@123")
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO users (id, username, full_name, email, password_hash, role, department, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (user_id, username, full_name, email, pw_hash, role.lower(), department, now),
        )
    return get_user_by_id(user_id)  # type: ignore


def authenticate_user(username_or_email: str, raw_password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username or email and verify password hash."""
    with db_session() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM users
            WHERE (LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)) AND is_active = 1
            """,
            (username_or_email.strip(), username_or_email.strip()),
        )
        row = cursor.fetchone()
        if not row:
            return None
        user = dict(row)
        stored_hash = user.get("password_hash")
        # If user has no password_hash yet, allow fallback for demo accounts and set hash
        if not stored_hash:
            stored_hash = hash_password(raw_password)
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (stored_hash, user["id"]))
        if verify_password(raw_password, stored_hash):
            return user
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user by ID."""
    with db_session() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieve user by username."""
    with db_session() as conn:
        cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_users(role: Optional[str] = None) -> List[Dict[str, Any]]:
    """List users, optionally filtered by role."""
    with db_session() as conn:
        if role:
            cursor = conn.execute("SELECT * FROM users WHERE role = ? AND is_active = 1 ORDER BY full_name", (role,))
        else:
            cursor = conn.execute("SELECT * FROM users WHERE is_active = 1 ORDER BY full_name")
        return [dict(r) for r in cursor.fetchall()]


# =====================================================================
# Blocks & Classrooms
# =====================================================================
def create_block(code: str, name: str, description: Optional[str] = None) -> Dict[str, Any]:
    """Create a campus block record."""
    block_id = f"BLK-{uuid.uuid4().hex[:6].upper()}"
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO blocks (id, code, name, description, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (block_id, code, name, description, now),
        )
    return get_block_by_id(block_id)  # type: ignore


def get_block_by_id(block_id: str) -> Optional[Dict[str, Any]]:
    """Get block by ID."""
    with db_session() as conn:
        cursor = conn.execute("SELECT * FROM blocks WHERE id = ?", (block_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_blocks() -> List[Dict[str, Any]]:
    """List all active campus blocks."""
    with db_session() as conn:
        cursor = conn.execute("SELECT * FROM blocks WHERE is_active = 1 ORDER BY code")
        return [dict(r) for r in cursor.fetchall()]


def create_classroom(
    block_id: str,
    room_number: str,
    name: str,
    floor: int = 1,
    qr_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a classroom record with a unique opaque QR token."""
    room_id = f"RM-{uuid.uuid4().hex[:8].upper()}"
    qr_code_token = qr_token or f"QR-ROOM-{uuid.uuid4().hex[:12].upper()}"
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO classrooms (id, block_id, room_number, name, floor, qr_code_token, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (room_id, block_id, room_number, name, floor, qr_code_token, now),
        )
    return get_classroom_by_id(room_id)  # type: ignore


def get_classroom_by_id(classroom_id: str) -> Optional[Dict[str, Any]]:
    """Get classroom with block metadata."""
    with db_session() as conn:
        cursor = conn.execute(
            """
            SELECT c.*, b.code AS block_code, b.name AS block_name
            FROM classrooms c
            JOIN blocks b ON c.block_id = b.id
            WHERE c.id = ?
            """,
            (classroom_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_classroom_by_qr_token(qr_token: str) -> Optional[Dict[str, Any]]:
    """Resolve classroom details from an opaque QR code token."""
    with db_session() as conn:
        cursor = conn.execute(
            """
            SELECT c.*, b.code AS block_code, b.name AS block_name
            FROM classrooms c
            JOIN blocks b ON c.block_id = b.id
            WHERE c.qr_code_token = ? AND c.is_active = 1
            """,
            (qr_token.strip(),),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def list_classrooms(block_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List classrooms, optionally filtered by block."""
    with db_session() as conn:
        if block_id:
            cursor = conn.execute(
                """
                SELECT c.*, b.code AS block_code, b.name AS block_name
                FROM classrooms c
                JOIN blocks b ON c.block_id = b.id
                WHERE c.block_id = ? AND c.is_active = 1
                ORDER BY c.room_number
                """,
                (block_id,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT c.*, b.code AS block_code, b.name AS block_name
                FROM classrooms c
                JOIN blocks b ON c.block_id = b.id
                WHERE c.is_active = 1
                ORDER BY b.code, c.room_number
                """
            )
        return [dict(r) for r in cursor.fetchall()]


# =====================================================================
# Technicians & Assignments
# =====================================================================
def create_technician(
    full_name: str,
    phone_number: str,
    email: str,
    specialty: str = "General AV",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a technician."""
    tech_id = f"TCH-{uuid.uuid4().hex[:6].upper()}"
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO technicians (id, user_id, full_name, phone_number, email, specialty, is_available, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
            """,
            (tech_id, user_id, full_name, phone_number, email, specialty, now),
        )
    return get_technician_by_id(tech_id)  # type: ignore


def get_technician_by_id(tech_id: str) -> Optional[Dict[str, Any]]:
    """Get technician details."""
    with db_session() as conn:
        cursor = conn.execute("SELECT * FROM technicians WHERE id = ?", (tech_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_technicians(available_only: bool = False) -> List[Dict[str, Any]]:
    """List technicians."""
    with db_session() as conn:
        query = "SELECT * FROM technicians WHERE is_active = 1"
        if available_only:
            query += " AND is_available = 1"
        query += " ORDER BY full_name"
        cursor = conn.execute(query)
        return [dict(r) for r in cursor.fetchall()]


def assign_technician(
    technician_id: str,
    block_id: Optional[str] = None,
    classroom_id: Optional[str] = None,
    equipment_category: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a routing assignment rule for a technician."""
    assign_id = f"ASN-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO technician_assignments (id, technician_id, block_id, classroom_id, equipment_category, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (assign_id, technician_id, block_id, classroom_id, equipment_category, now),
        )
    return {"id": assign_id, "technician_id": technician_id}


def find_assigned_technician(
    classroom_id: str,
    block_id: Optional[str] = None,
    equipment_category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Route complaint to the most specific available technician:
    1. Exact Classroom assignment
    2. Block + Equipment category
    3. Block assignment
    4. General fallback available technician
    """
    with db_session() as conn:
        # 1. Match specific classroom
        cursor = conn.execute(
            """
            SELECT t.* FROM technicians t
            JOIN technician_assignments ta ON t.id = ta.technician_id
            WHERE ta.classroom_id = ? AND t.is_active = 1 AND t.is_available = 1
            LIMIT 1
            """,
            (classroom_id,),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        # Resolve block_id if not given
        if not block_id:
            room = get_classroom_by_id(classroom_id)
            if room:
                block_id = room["block_id"]

        # 2. Match block and equipment category
        if block_id and equipment_category:
            cursor = conn.execute(
                """
                SELECT t.* FROM technicians t
                JOIN technician_assignments ta ON t.id = ta.technician_id
                WHERE ta.block_id = ? AND ta.equipment_category = ? AND t.is_active = 1 AND t.is_available = 1
                LIMIT 1
                """,
                (block_id, equipment_category),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

        # 3. Match block
        if block_id:
            cursor = conn.execute(
                """
                SELECT t.* FROM technicians t
                JOIN technician_assignments ta ON t.id = ta.technician_id
                WHERE ta.block_id = ? AND t.is_active = 1 AND t.is_available = 1
                LIMIT 1
                """,
                (block_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)

        # 4. Fallback to any active available technician
        cursor = conn.execute(
            "SELECT * FROM technicians WHERE is_active = 1 AND is_available = 1 ORDER BY RANDOM() LIMIT 1"
        )
        row = cursor.fetchone()
        if row:
            return dict(row)

        # 5. Fallback to any technician
        cursor = conn.execute("SELECT * FROM technicians WHERE is_active = 1 LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None


# =====================================================================
# Complaints & Lifecycle
# =====================================================================
def create_complaint(
    classroom_id: str,
    device_type: str,
    problem_description: str,
    device_model: Optional[str] = None,
    parsed_symptoms: Optional[str] = None,
    urgency: str = "Medium",
    reporter_user_id: Optional[str] = None,
    auto_assign: bool = True,
) -> Dict[str, Any]:
    """Register a new complaint and record audit log."""
    complaint_id = f"CMP-{uuid.uuid4().hex[:8].upper()}"
    date_prefix = datetime.now().strftime("%Y%m%d")
    complaint_code = f"AV-{date_prefix}-{uuid.uuid4().hex[:5].upper()}"
    now = utc_now_iso()

    assigned_tech_id = None
    if auto_assign:
        tech = find_assigned_technician(classroom_id=classroom_id, equipment_category=device_type)
        if tech:
            assigned_tech_id = tech["id"]

    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO complaints (
                id, complaint_code, classroom_id, reporter_user_id, device_type,
                device_model, problem_description, parsed_symptoms, urgency,
                status, assigned_technician_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
            """,
            (
                complaint_id,
                complaint_code,
                classroom_id,
                reporter_user_id,
                device_type,
                device_model or "unspecified",
                problem_description,
                parsed_symptoms or problem_description,
                urgency,
                assigned_tech_id,
                now,
                now,
            ),
        )

        # Audit Event: Created
        log_complaint_event(
            complaint_id=complaint_id,
            event_type="complaint_created",
            actor_name="System/Reporter",
            actor_role="teacher",
            details={"problem": problem_description, "device": device_type, "urgency": urgency},
            conn=conn,
        )

        if assigned_tech_id:
            log_complaint_event(
                complaint_id=complaint_id,
                event_type="technician_assigned",
                actor_name="AutoRouter",
                actor_role="system",
                details={"assigned_technician_id": assigned_tech_id},
                conn=conn,
            )

    return get_complaint_by_id(complaint_id)  # type: ignore


def get_complaint_by_id(complaint_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full complaint details with classroom and technician names."""
    with db_session() as conn:
        cursor = conn.execute(
            """
            SELECT c.*,
                   cl.room_number, cl.name AS classroom_name,
                   b.code AS block_code, b.name AS block_name,
                   t.full_name AS technician_name, t.phone_number AS technician_phone, t.email AS technician_email
            FROM complaints c
            JOIN classrooms cl ON c.classroom_id = cl.id
            JOIN blocks b ON cl.block_id = b.id
            LEFT JOIN technicians t ON c.assigned_technician_id = t.id
            WHERE c.id = ?
            """,
            (complaint_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def find_existing_unresolved_complaint(classroom_id: str, device_type: str) -> Optional[Dict[str, Any]]:
    """Detect if an active complaint already exists for this room and device type."""
    with db_session() as conn:
        cursor = conn.execute(
            """
            SELECT c.*, cl.room_number, b.code AS block_code
            FROM complaints c
            JOIN classrooms cl ON c.classroom_id = cl.id
            JOIN blocks b ON cl.block_id = b.id
            WHERE c.classroom_id = ? AND c.device_type = ? AND c.status IN ('pending', 'in_progress', 'escalated')
            ORDER BY c.created_at DESC LIMIT 1
            """,
            (classroom_id, device_type),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def update_complaint_status(
    complaint_id: str,
    status: str,
    actor_name: str,
    actor_role: str,
    resolution_notes: Optional[str] = None,
    resolved_by_user_id: Optional[str] = None,
    assigned_technician_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update complaint status and record audit event in a single transaction."""
    norm_role = (actor_role or "").lower()
    if status in ("resolved", "closed") and norm_role not in ("admin", "administrator", "technician", "system", "teacher", "faculty"):
        raise PermissionError(f"Role '{actor_role}' is not authorized to resolve complaints.")
    if status == "in_progress" and norm_role not in ("admin", "technician", "system"):
        raise PermissionError(f"Role '{actor_role}' is not authorized to acknowledge complaints.")
    now = utc_now_iso()
    with db_session() as conn:
        current = conn.execute("SELECT status FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if not current:
            return None
        old_status = current["status"]

        resolved_at = now if status == "resolved" else None

        updates = ["status = ?", "updated_at = ?"]
        params: List[Any] = [status, now]

        if status == "resolved":
            updates.extend(["resolution_notes = ?", "resolved_at = ?", "resolved_by_user_id = ?"])
            params.extend([resolution_notes or "Resolved confirmed", resolved_at, resolved_by_user_id])
        elif resolution_notes:
            updates.append("resolution_notes = ?")
            params.append(resolution_notes)

        if assigned_technician_id:
            updates.append("assigned_technician_id = ?")
            params.append(assigned_technician_id)

        params.append(complaint_id)
        sql = f"UPDATE complaints SET {', '.join(updates)} WHERE id = ?"
        conn.execute(sql, params)

        # Audit event
        log_complaint_event(
            complaint_id=complaint_id,
            event_type="status_changed",
            actor_name=actor_name,
            actor_role=actor_role,
            details={
                "old_status": old_status,
                "new_status": status,
                "notes": resolution_notes,
                "resolved_at": resolved_at,
            },
            conn=conn,
        )

    return get_complaint_by_id(complaint_id)


def list_complaints(
    status: Optional[str] = None,
    block_id: Optional[str] = None,
    device_type: Optional[str] = None,
    technician_id: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Filter and search complaints."""
    with db_session() as conn:
        conditions = ["1=1"]
        params: List[Any] = []

        if status and status != "All":
            conditions.append("c.status = ?")
            params.append(status.lower())

        if block_id and block_id != "All":
            conditions.append("cl.block_id = ?")
            params.append(block_id)

        if device_type and device_type != "All":
            conditions.append("c.device_type = ?")
            params.append(device_type)

        if technician_id and technician_id != "All":
            conditions.append("c.assigned_technician_id = ?")
            params.append(technician_id)

        if search:
            conditions.append("(c.complaint_code LIKE ? OR c.problem_description LIKE ? OR cl.room_number LIKE ?)")
            s_param = f"%{search.strip()}%"
            params.extend([s_param, s_param, s_param])

        params.append(limit)
        sql = f"""
            SELECT c.*,
                   cl.room_number, cl.name AS classroom_name,
                   b.code AS block_code, b.name AS block_name,
                   t.full_name AS technician_name
            FROM complaints c
            JOIN classrooms cl ON c.classroom_id = cl.id
            JOIN blocks b ON cl.block_id = b.id
            LEFT JOIN technicians t ON c.assigned_technician_id = t.id
            WHERE {' AND '.join(conditions)}
            ORDER BY c.created_at DESC
            LIMIT ?
        """
        cursor = conn.execute(sql, params)
        return [dict(r) for r in cursor.fetchall()]


def get_latest_complaints(limit: int = 5) -> List[Dict[str, Any]]:
    """Return the most recent complaints for the floating/collapsible dashboard panel."""
    return list_complaints(limit=limit)


# =====================================================================
# Chat & Troubleshooting Steps
# =====================================================================
def add_chat_message(
    complaint_id: str,
    sender_role: str,
    message_text: str,
    retrieved_sources: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Store chat message associated with a complaint."""
    msg_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now_iso()
    sources_json = json.dumps(retrieved_sources) if retrieved_sources else None
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (id, complaint_id, sender_role, message_text, retrieved_sources_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (msg_id, complaint_id, sender_role, message_text, sources_json, now),
        )
    return {"id": msg_id, "complaint_id": complaint_id, "role": sender_role, "text": message_text}


def get_chat_messages(complaint_id: str) -> List[Dict[str, Any]]:
    """Retrieve all chat messages for a complaint in chronological order."""
    with db_session() as conn:
        cursor = conn.execute(
            "SELECT * FROM chat_messages WHERE complaint_id = ? ORDER BY created_at ASC",
            (complaint_id,),
        )
        results = []
        for r in cursor.fetchall():
            d = dict(r)
            if d.get("retrieved_sources_json"):
                try:
                    d["retrieved_sources"] = json.loads(d["retrieved_sources_json"])
                except Exception:
                    d["retrieved_sources"] = []
            results.append(d)
        return results


def add_troubleshooting_step(
    complaint_id: str,
    step_number: int,
    instruction_text: str,
    source_doc: Optional[str] = None,
    source_page: Optional[int] = None,
) -> Dict[str, Any]:
    """Record a troubleshooting step prescribed to the user."""
    step_id = f"STP-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO troubleshooting_steps (id, complaint_id, step_number, instruction_text, source_doc, source_page, user_feedback, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (step_id, complaint_id, step_number, instruction_text, source_doc, source_page, now),
        )
        log_complaint_event(
            complaint_id=complaint_id,
            event_type="step_suggested",
            actor_name="Qwen3-8B Assistant",
            actor_role="assistant",
            details={"step_number": step_number, "instruction": instruction_text, "source": source_doc},
            conn=conn,
        )
    return {"id": step_id, "step_number": step_number, "instruction": instruction_text}


def record_step_feedback(
    complaint_id: str,
    step_number: int,
    user_feedback: str,
    actor_name: str = "Faculty Member",
) -> None:
    """Record teacher's feedback on a troubleshooting step ('worked', 'failed', 'skipped')."""
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE troubleshooting_steps
            SET user_feedback = ?, feedback_timestamp = ?
            WHERE complaint_id = ? AND step_number = ?
            """,
            (user_feedback, now, complaint_id, step_number),
        )
        log_complaint_event(
            complaint_id=complaint_id,
            event_type="step_feedback_recorded",
            actor_name=actor_name,
            actor_role="teacher",
            details={"step_number": step_number, "feedback": user_feedback},
            conn=conn,
        )


def get_troubleshooting_steps(complaint_id: str) -> List[Dict[str, Any]]:
    """Get all steps and feedback for a complaint."""
    with db_session() as conn:
        cursor = conn.execute(
            "SELECT * FROM troubleshooting_steps WHERE complaint_id = ? ORDER BY step_number ASC",
            (complaint_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


# =====================================================================
# Audit Log & Complaint Events
# =====================================================================
def log_complaint_event(
    complaint_id: str,
    event_type: str,
    actor_name: str,
    actor_role: str,
    details: Optional[Dict[str, Any]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Append a persistent audit event for a complaint."""
    event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now_iso()
    details_json = json.dumps(details or {})

    def _execute(c: sqlite3.Connection):
        c.execute(
            """
            INSERT INTO complaint_events (id, complaint_id, event_type, actor_name, actor_role, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, complaint_id, event_type, actor_name, actor_role, details_json, now),
        )

    if conn:
        _execute(conn)
    else:
        with db_session() as c:
            _execute(c)

    return {"id": event_id, "event_type": event_type, "timestamp": now}


def get_complaint_events(complaint_id: str) -> List[Dict[str, Any]]:
    """Retrieve full audit timeline for a complaint."""
    with db_session() as conn:
        cursor = conn.execute(
            "SELECT * FROM complaint_events WHERE complaint_id = ? ORDER BY created_at ASC",
            (complaint_id,),
        )
        events = []
        for r in cursor.fetchall():
            d = dict(r)
            if d.get("details_json"):
                try:
                    d["details"] = json.loads(d["details_json"])
                except Exception:
                    d["details"] = {}
            events.append(d)
        return events


# =====================================================================
# Notifications & Twilio Logs
# =====================================================================
def log_notification(
    complaint_id: str,
    technician_id: str,
    channel: str,
    recipient_contact: str,
    message: str,
    status: str = "pending",
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Record an in-app or Twilio call notification attempt."""
    notif_id = f"NTF-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now_iso()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO notifications (id, complaint_id, technician_id, channel, recipient_contact, message, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (notif_id, complaint_id, technician_id, channel, recipient_contact, message, status, error_message, now),
        )
        log_complaint_event(
            complaint_id=complaint_id,
            event_type=f"notification_{channel}_{status}",
            actor_name="NotificationService",
            actor_role="system",
            details={"recipient": recipient_contact, "channel": channel, "status": status, "error": error_message},
            conn=conn,
        )
    return {"id": notif_id, "channel": channel, "status": status}


def list_notifications(complaint_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List notification logs."""
    with db_session() as conn:
        if complaint_id:
            cursor = conn.execute(
                "SELECT * FROM notifications WHERE complaint_id = ? ORDER BY created_at DESC",
                (complaint_id,),
            )
        else:
            cursor = conn.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50")
        return [dict(r) for r in cursor.fetchall()]


# =====================================================================
# Knowledge Documents Table
# =====================================================================
def register_knowledge_document(
    title: str,
    filename: str,
    file_type: str,
    file_path: str,
    total_chunks: int,
    uploaded_by: str = "admin",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Save record of an uploaded manual."""
    doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
    now = utc_now_iso()
    meta_json = json.dumps(metadata or {})
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO knowledge_documents (id, title, filename, file_type, file_path, total_chunks, doc_metadata_json, uploaded_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, title, filename, file_type, file_path, total_chunks, meta_json, uploaded_by, now),
        )
    return {"id": doc_id, "title": title, "filename": filename, "total_chunks": total_chunks}


def list_knowledge_documents() -> List[Dict[str, Any]]:
    """List all registered knowledge documents."""
    with db_session() as conn:
        cursor = conn.execute("SELECT * FROM knowledge_documents ORDER BY created_at DESC")
        return [dict(r) for r in cursor.fetchall()]


# =====================================================================
# Live Metrics & Dashboard Queries
# =====================================================================
def get_live_metrics() -> Dict[str, Any]:
    """Compute real-time metrics directly from SQLite database queries.

    Never uses hard-coded demo counts!
    """
    with db_session() as conn:
        # Total complaints
        total = conn.execute("SELECT COUNT(*) AS c FROM complaints").fetchone()["c"]

        # Counts by status
        resolved = conn.execute("SELECT COUNT(*) AS c FROM complaints WHERE status = 'resolved'").fetchone()["c"]
        pending = conn.execute("SELECT COUNT(*) AS c FROM complaints WHERE status = 'pending'").fetchone()["c"]
        escalated = conn.execute("SELECT COUNT(*) AS c FROM complaints WHERE status = 'escalated'").fetchone()["c"]
        in_progress = conn.execute("SELECT COUNT(*) AS c FROM complaints WHERE status = 'in_progress'").fetchone()["c"]

        # Average resolution time from stored timestamps (created_at to resolved_at)
        cursor = conn.execute(
            """
            SELECT created_at, resolved_at FROM complaints
            WHERE status = 'resolved' AND resolved_at IS NOT NULL
            """
        )
        resolved_rows = cursor.fetchall()
        avg_res_minutes = 0.0
        if resolved_rows:
            diffs = []
            for r in resolved_rows:
                try:
                    c_dt = datetime.fromisoformat(r["created_at"])
                    r_dt = datetime.fromisoformat(r["resolved_at"])
                    diff_min = (r_dt - c_dt).total_seconds() / 60.0
                    if diff_min >= 0:
                        diffs.append(diff_min)
                except Exception:
                    pass
            if diffs:
                avg_res_minutes = round(sum(diffs) / len(diffs), 1)

        # Device-wise complaint distribution
        cursor = conn.execute(
            """
            SELECT device_type, COUNT(*) AS count
            FROM complaints
            GROUP BY device_type
            ORDER BY count DESC
            """
        )
        device_distribution = {r["device_type"]: r["count"] for r in cursor.fetchall()}

        # Daily complaints trend (last 7 days or all days)
        cursor = conn.execute(
            """
            SELECT SUBSTR(created_at, 1, 10) AS day, COUNT(*) AS count
            FROM complaints
            GROUP BY day
            ORDER BY day ASC
            LIMIT 30
            """
        )
        trend = {r["day"]: r["count"] for r in cursor.fetchall()}

        return {
            "total_complaints": total,
            "resolved_complaints": resolved,
            "pending_complaints": pending,
            "escalated_complaints": escalated,
            "in_progress_complaints": in_progress,
            "average_resolution_time_minutes": avg_res_minutes,
            "device_distribution": device_distribution,
            "trend_by_day": trend,
        }

