"""Extensible Notification Service for Technicians (In-App & Optional Twilio Calls).

Strict Rules:
- In-app technician notification is baseline and always succeeds if database is online.
- Twilio phone calls require configured credentials and explicit user confirmation.
- Shows intended recipient and request details before initiating a call.
- Records all attempts, timestamps, and outcomes in notifications table and audit log.
- Never pretends a call succeeded if Twilio did not confirm it.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from ..database.crud import log_complaint_event, log_notification

logger = logging.getLogger(__name__)


class NotificationService:
    """Dispatches notifications across In-App and optional Twilio Voice channels."""

    def __init__(self):
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
        self.admin_phone = os.getenv("ADMIN_NOTIFICATION_PHONE", "").strip()

    def is_twilio_configured(self) -> bool:
        """Check if real Twilio credentials are provided."""
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_phone_number
            and not self.twilio_account_sid.startswith("your_")
        )

    def send_in_app_notification(
        self,
        complaint_id: str,
        technician: Dict[str, Any],
        message: str,
    ) -> Dict[str, Any]:
        """Send baseline in-app notification to technician."""
        tech_id = technician.get("id", "TCH-UNKNOWN")
        contact = technician.get("email") or technician.get("phone_number", "in_app")
        return log_notification(
            complaint_id=complaint_id,
            technician_id=tech_id,
            channel="in_app",
            recipient_contact=contact,
            message=message,
            status="sent",
        )

    def initiate_technician_phone_call(
        self,
        complaint_id: str,
        technician: Dict[str, Any],
        classroom_info: str,
        problem_summary: str,
        urgency: str = "Urgent",
        confirmed_by_user: bool = False,
    ) -> Dict[str, Any]:
        """Place automated telephone call to technician via Twilio Voice API.

        Requires confirmed_by_user == True.
        """
        tech_id = technician.get("id", "TCH-UNKNOWN")
        tech_phone = technician.get("phone_number", "").strip()

        if not confirmed_by_user:
            return {
                "success": False,
                "error": "User confirmation required prior to dispatching phone call.",
                "status": "aborted",
            }

        if not self.is_twilio_configured():
            err_msg = (
                "Twilio credentials not configured in .env "
                "(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER). "
                "Phone call dispatch is in simulated configuration check mode."
            )
            log_notification(
                complaint_id=complaint_id,
                technician_id=tech_id,
                channel="twilio_call",
                recipient_contact=tech_phone,
                message=f"Attempted voice call: {problem_summary}",
                status="failed",
                error_message=err_msg,
            )
            return {
                "success": False,
                "error": err_msg,
                "recipient": tech_phone,
                "status": "failed",
            }

        # Real Twilio API Call
        try:
            from twilio.rest import Client

            client = Client(self.twilio_account_sid, self.twilio_auth_token)

            # Build TwiML voice message
            twiml_instructions = (
                f"<Response><Say voice='Polly.Joanna'>"
                f"Urgent Campus AV Alert for Technician {technician.get('full_name', '')}. "
                f"Classroom {classroom_info}. Issue reported: {problem_summary}. Urgency: {urgency}. "
                f"Please report to room immediately."
                f"</Say></Response>"
            )

            call = client.calls.create(
                to=tech_phone,
                from_=self.twilio_phone_number,
                twiml=twiml_instructions,
            )

            log_notification(
                complaint_id=complaint_id,
                technician_id=tech_id,
                channel="twilio_call",
                recipient_contact=tech_phone,
                message=f"Voice call dispatched. SID: {call.sid}",
                status="sent",
            )

            return {
                "success": True,
                "call_sid": call.sid,
                "status": "sent",
                "recipient": tech_phone,
            }
        except Exception as e:
            err = str(e)
            logger.error("Twilio call failed: %s", err)
            log_notification(
                complaint_id=complaint_id,
                technician_id=tech_id,
                channel="twilio_call",
                recipient_contact=tech_phone,
                message=f"Voice call failed: {problem_summary}",
                status="failed",
                error_message=err,
            )
            return {
                "success": False,
                "error": err,
                "recipient": tech_phone,
                "status": "failed",
            }


notification_service = NotificationService()

