"""End-to-End Orchestrator for Complaint Processing & AI Guided Troubleshooting."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from ..database.crud import (
    add_chat_message,
    add_troubleshooting_step,
    create_complaint,
    find_assigned_technician,
    find_existing_unresolved_complaint,
    get_classroom_by_id,
    get_complaint_by_id,
    get_troubleshooting_steps,
    log_complaint_event,
    record_step_feedback,
    update_complaint_status,
)
from ..model.llm_inference import inference_engine
from ..nlp.extractor import AVQueryExtractor
from ..rag.vector_store import vector_store
from .notification_service import notification_service

logger = logging.getLogger(__name__)


class ComplaintService:
    """Coordinates lifecycle from teacher submission to AI troubleshooting and technician escalation."""

    @classmethod
    def initiate_troubleshooting_session(
        cls,
        classroom_id: str,
        problem_description: str,
        device_type: Optional[str] = None,
        device_model: Optional[str] = None,
        reporter_user_id: Optional[str] = None,
        urgency: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a new troubleshooting session:
        1. NLP Entity & safety hazard extraction
        2. SQLite Complaint record creation with unique ID
        3. ChromaDB manual retrieval
        4. Qwen3-8B step generation
        5. Audit logging
        """
        # 1. NLP Extraction
        nlp_res = AVQueryExtractor.parse_query(problem_description, current_device=device_type)
        resolved_device = device_type or nlp_res["device_type"]
        resolved_urgency = urgency or nlp_res["urgency"]
        is_safety = nlp_res["is_safety_hazard"]
        hazard_details = nlp_res["hazard_details"]

        # 2. Classroom context
        classroom = get_classroom_by_id(classroom_id)
        room_label = f"{classroom['block_code']}-{classroom['room_number']}" if classroom else "Classroom"

        # 3. Create SQLite Complaint Record
        complaint = create_complaint(
            classroom_id=classroom_id,
            device_type=resolved_device,
            problem_description=problem_description,
            device_model=device_model,
            parsed_symptoms=",".join(nlp_res["symptoms"]) if nlp_res["symptoms"] else problem_description,
            urgency=resolved_urgency,
            reporter_user_id=reporter_user_id,
            auto_assign=True,
        )
        complaint_id = complaint["id"]

        # Log AI Session started
        log_complaint_event(
            complaint_id=complaint_id,
            event_type="ai_troubleshooting_started",
            actor_name="AI Assistant",
            actor_role="assistant",
            details={"is_safety_hazard": is_safety, "model": inference_engine.model_id},
        )

        # Record User's Initial Message
        add_chat_message(
            complaint_id=complaint_id,
            sender_role="user",
            message_text=problem_description,
        )

        # 4. RAG Retrieval from ChromaDB
        retrieved_evidence = []
        if not is_safety:
            query = f"{resolved_device} {problem_description} {' '.join(nlp_res['symptoms'])}"
            retrieved_evidence = vector_store.query(
                query_text=query,
                equipment_category=resolved_device,
                top_k=3,
            )

        # 5. Qwen3-8B Generation
        ai_response = inference_engine.generate_troubleshooting_response(
            device_type=resolved_device,
            user_problem=problem_description,
            classroom_context=classroom or {},
            retrieved_evidence=retrieved_evidence,
            conversation_history=[],
            step_number=1,
            is_safety_hazard=is_safety,
            hazard_details=hazard_details,
        )

        # Record Assistant Message in DB
        add_chat_message(
            complaint_id=complaint_id,
            sender_role="assistant",
            message_text=ai_response["troubleshooting_instruction"],
            retrieved_sources=retrieved_evidence,
        )

        # Store step in database
        step_rec = add_troubleshooting_step(
            complaint_id=complaint_id,
            step_number=1,
            instruction_text=ai_response["troubleshooting_instruction"],
            source_doc=ai_response.get("source_attribution"),
            source_page=1,
        )

        # Handle Immediate Safety Escalation if detected
        if is_safety:
            update_complaint_status(
                complaint_id=complaint_id,
                status="escalated",
                actor_name="System Safety Guard",
                actor_role="system",
                resolution_notes="Immediate safety hazard escalation (Smoke/Electrical).",
            )
            # Dispatch in-app notification
            tech = find_assigned_technician(classroom_id=classroom_id, equipment_category=resolved_device)
            if tech:
                notification_service.send_in_app_notification(
                    complaint_id=complaint_id,
                    technician=tech,
                    message=f"CRITICAL SAFETY HAZARD in {room_label}: {hazard_details}",
                )

        return {
            "complaint": complaint,
            "ai_response": ai_response,
            "retrieved_evidence": retrieved_evidence,
            "nlp_analysis": nlp_res,
            "step": step_rec,
        }

    @classmethod
    def process_step_feedback_and_next(
        cls,
        complaint_id: str,
        step_number: int,
        feedback: str,  # 'worked', 'failed', 'skipped'
        user_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process user feedback on a step and generate next step or close complaint."""
        complaint = get_complaint_by_id(complaint_id)
        if not complaint:
            raise ValueError(f"Complaint {complaint_id} not found.")

        # 1. Record feedback
        record_step_feedback(
            complaint_id=complaint_id,
            step_number=step_number,
            user_feedback=feedback,
            actor_name="Faculty Member",
        )

        # 2. If it worked -> Ask confirmation & mark resolved
        if feedback == "worked":
            resolved_complaint = update_complaint_status(
                complaint_id=complaint_id,
                status="resolved",
                actor_name="Faculty Member",
                actor_role="teacher",
                resolution_notes=f"Resolved successfully by teacher via AI Step {step_number}.",
            )
            congrats_msg = (
                "🎉 **Excellent! The issue is resolved.**\n\n"
                f"Complaint `{complaint['complaint_code']}` has been marked as **Resolved** in the campus system.\n"
                "Thank you for troubleshooting!"
            )
            add_chat_message(
                complaint_id=complaint_id,
                sender_role="assistant",
                message_text=congrats_msg,
            )
            return {
                "status": "resolved",
                "message": congrats_msg,
                "complaint": resolved_complaint,
            }

        # 3. If it failed or skipped -> Check if next step available from RAG
        next_step_num = step_number + 1
        device = complaint["device_type"]
        problem = complaint["problem_description"]

        retrieved_evidence = vector_store.query(
            query_text=f"{device} {problem} step {next_step_num}",
            equipment_category=device,
            top_k=3,
        )

        ai_response = inference_engine.generate_troubleshooting_response(
            device_type=device,
            user_problem=problem,
            classroom_context={"room_number": complaint.get("room_number")},
            retrieved_evidence=retrieved_evidence,
            conversation_history=[],
            step_number=next_step_num,
        )

        # If model recommends escalation or steps exceeded
        if ai_response.get("recommend_escalation") or next_step_num > 4:
            escalate_msg = (
                f"⚠️ Troubleshooting steps did not resolve the fault with the **{device}**.\n\n"
                "I am ready to escalate this request to your assigned technician. "
                "Would you like to dispatch the technician now?"
            )
            add_chat_message(
                complaint_id=complaint_id,
                sender_role="assistant",
                message_text=escalate_msg,
            )
            return {
                "status": "offer_escalation",
                "message": escalate_msg,
                "complaint": complaint,
            }

        # Save and return next step
        add_chat_message(
            complaint_id=complaint_id,
            sender_role="assistant",
            message_text=ai_response["troubleshooting_instruction"],
            retrieved_sources=retrieved_evidence,
        )
        add_troubleshooting_step(
            complaint_id=complaint_id,
            step_number=next_step_num,
            instruction_text=ai_response["troubleshooting_instruction"],
            source_doc=ai_response.get("source_attribution"),
            source_page=1,
        )

        return {
            "status": "next_step",
            "step_number": next_step_num,
            "ai_response": ai_response,
            "complaint": complaint,
        }

    @classmethod
    def escalate_to_technician(
        cls,
        complaint_id: str,
        escalation_reason: str = "Troubleshooting steps failed",
        dispatch_voice_call: bool = False,
        confirmed_by_user: bool = False,
    ) -> Dict[str, Any]:
        """Escalate complaint to assigned technician and trigger notifications."""
        complaint = get_complaint_by_id(complaint_id)
        if not complaint:
            raise ValueError(f"Complaint {complaint_id} not found.")

        # Ensure technician is assigned
        tech = None
        if complaint.get("assigned_technician_id"):
            from ..database.crud import get_technician_by_id
            tech = get_technician_by_id(complaint["assigned_technician_id"])

        if not tech:
            tech = find_assigned_technician(
                classroom_id=complaint["classroom_id"],
                equipment_category=complaint["device_type"],
            )

        if not tech:
            from ..database.crud import db_session
            with db_session() as conn:
                r = conn.execute("SELECT * FROM technicians WHERE is_active = 1 LIMIT 1").fetchone()
                if r:
                    tech = dict(r)

        tech_id = tech["id"] if tech else None

        updated_complaint = update_complaint_status(
            complaint_id=complaint_id,
            status="escalated",
            actor_name="Faculty Member",
            actor_role="teacher",
            resolution_notes=f"Escalated to technician: {escalation_reason}",
            assigned_technician_id=tech_id,
        )

        room_label = f"{complaint.get('block_code', '')}-{complaint.get('room_number', '')}"
        notif_msg = f"Escalated Complaint [{complaint['complaint_code']}] for {complaint['device_type']} in {room_label}. Reason: {escalation_reason}"

        # In-app notification
        in_app_res = {}
        if tech:
            in_app_res = notification_service.send_in_app_notification(
                complaint_id=complaint_id,
                technician=tech,
                message=notif_msg,
            )

        # Ensure a ticket is created/tracked for technician workspace
        try:
            from ..repository import repository
            repository.create_ticket(
                complaint_id=complaint_id,
                title=f"Field Dispatch: {complaint.get('device_type', 'AV')} in {room_label}",
                device_type=complaint.get("device_type", "projector"),
                room_no=complaint.get("room_number", "Room"),
                priority=complaint.get("urgency", "High"),
                technician_notes=f"Auto-dispatched via AI Troubleshooting: {escalation_reason}",
            )
        except Exception:
            pass

        # Optional Twilio Voice call
        voice_res = None
        if dispatch_voice_call and tech and confirmed_by_user:
            voice_res = notification_service.initiate_technician_phone_call(
                complaint_id=complaint_id,
                technician=tech,
                classroom_info=room_label,
                problem_summary=complaint["problem_description"],
                urgency=complaint["urgency"],
                confirmed_by_user=True,
            )

        return {
            "complaint": updated_complaint,
            "assigned_technician": tech,
            "in_app_notification": in_app_res,
            "voice_call": voice_res,
        }


complaint_service = ComplaintService()

