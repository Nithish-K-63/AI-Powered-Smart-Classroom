"""Natural Language Processing and Intent/Entity Extraction for AV Complaints.

Extracts:
- Equipment Type: projector, microphone, smart board, speaker, display, doc_cam, amplifier
- Symptoms & Fault Signals: power, display, audio, connection, distortion, stylus, etc.
- Safety Hazards: smoke, spark, burn smell, electric shock, exposed wire, fire risk
- Urgency: Urgent, High, Medium, Low
- Troubleshooting Intent: troubleshoot, escalate, confirm_fix, question
- Location hints: room numbers, block names
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Supported AV equipment types & keywords
EQUIPMENT_KEYWORDS: Dict[str, List[str]] = {
    "projector": ["projector", "projection", "beamer", "epson", "benq", "optoma", "bulb", "lamp"],
    "smart_board": ["smart board", "smartboard", "interactive whiteboard", "stylus", "promethean", "maxhub", "touch screen", "touchscreen", "clevertouch", "digital board"],
    "microphone": ["microphone", "mic", "mic audio", "shure", "sennheiser", "lapel", "collar mic", "wireless mic", "handheld mic", "podium mic"],
    "speaker": ["speaker", "speakers", "loudspeaker", "audio system", "pa system", "sound system", "amplifier", "amp", "subwoofer"],
    "display": ["display", "monitor", "tv", "television", "screen", "lg display", "samsung display", "hdmi screen"],
    "document_camera": ["document camera", "doc cam", "visualizer", "aver", "elmo"],
}

# Safety critical hazard keywords
SAFETY_HAZARD_KEYWORDS: List[str] = [
    "smoke", "smoking", "spark", "sparking", "sparks", "burning", "burnt smell",
    "burning smell", "fire", "electric shock", "shock", "shocking", "short circuit",
    "exposed wire", "exposed wiring", "popping sound", "explod", "melted", "smell of burning"
]

# Urgency keywords
URGENCY_KEYWORDS: Dict[str, List[str]] = {
    "Urgent": ["immediate", "urgent", "critical", "exam", "test", "lecture started", "class started", "emergency", "asap", "now", "live session", "symposium", "conference"],
    "High": ["soon", "important", "starting in 5", "starting in 10", "high priority", "intermittent failure", "failing frequently"],
    "Low": ["whenever", "minor", "not urgent", "routine", "next week", "later today"],
}

# Standard symptom patterns
SYMPTOM_PATTERNS: Dict[str, List[str]] = {
    "no_power": ["won't turn on", "does not turn on", "no power", "dead", "power led off", "black screen", "completely off"],
    "no_display": ["no image", "no display", "blank screen", "no signal", "blue screen", "input not found", "black screen"],
    "blurry_distorted_image": ["blurry", "fuzzy", "distorted", "flickering", "flicker", "wrong resolution", "aspect ratio", "stretched"],
    "no_sound": ["no sound", "no audio", "silent", "cannot hear", "speaker quiet", "muted"],
    "audio_distortion": ["static", "buzzing", "humming", "echo", "feedback", "crackling", "muffled"],
    "touch_stylus_issue": ["touch not working", "stylus not writing", "stylus offset", "calibration off", "pen not working", "ghost touch"],
    "cable_connection": ["cable loose", "hdmi disconnected", "vga broken", "port loose", "adapter broken", "usb disconnect"],
    "wireless_sharing": ["airplay failed", "miracast failed", "cannot cast", "wireless display error", "screen sharing failed"],
}


class AVQueryExtractor:
    """Extracts structured entities, symptoms, urgency, and safety hazards from user inputs."""

    @classmethod
    def detect_safety_hazard(cls, text: str) -> Optional[str]:
        """Detect safety-critical hazards.

        Returns detected hazard description if found, else None.
        """
        lower = text.lower()
        for kw in SAFETY_HAZARD_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return f"Safety hazard detected: '{kw}'. Electrical or thermal risk."
        return None

    @classmethod
    def extract_equipment_type(cls, text: str, default: Optional[str] = None) -> Optional[str]:
        """Detect equipment category from text."""
        lower = text.lower()
        for eq_type, keywords in EQUIPMENT_KEYWORDS.items():
            for kw in keywords:
                if kw in lower:
                    return eq_type
        return default

    @classmethod
    def extract_symptoms(cls, text: str) -> List[str]:
        """Extract identified symptom labels from text."""
        lower = text.lower()
        detected = []
        for sym_label, patterns in SYMPTOM_PATTERNS.items():
            for pat in patterns:
                if pat in lower:
                    detected.append(sym_label)
                    break
        return detected

    @classmethod
    def extract_urgency(cls, text: str, default: str = "Medium") -> str:
        """Extract urgency level."""
        lower = text.lower()
        for urgency_lvl, kws in URGENCY_KEYWORDS.items():
            for kw in kws:
                if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                    return urgency_lvl
        return default

    @classmethod
    def extract_classroom_number(cls, text: str) -> Optional[str]:
        """Extract room number patterns like 'Room 102', 'B-14', 'Lab 3', 'E15'."""
        match = re.search(r"\b([A-Z]?\d{2,3}[A-Z]?|[A-Z]-\d{2,3}|LH-\d+|Lab\s*\d+)\b", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

    @classmethod
    def check_missing_information(
        cls,
        device_type: Optional[str],
        symptom_description: str,
    ) -> Optional[str]:
        """Determine if essential information is missing and generate a follow-up question."""
        if not device_type or device_type == "other":
            return "Could you specify which AV device is experiencing trouble (e.g., Projector, Smart Board, Microphone, Speaker, or Display)?"
        if len(symptom_description.strip()) < 8:
            return f"Could you provide a few more details about what is happening with the {device_type.replace('_', ' ')}?"
        return None

    @classmethod
    def parse_query(cls, text: str, current_device: Optional[str] = None) -> Dict[str, Any]:
        """Perform comprehensive extraction on a user complaint message."""
        hazard = cls.detect_safety_hazard(text)
        device = cls.extract_equipment_type(text, default=current_device)
        symptoms = cls.extract_symptoms(text)
        urgency = cls.extract_urgency(text)
        room_candidate = cls.extract_classroom_number(text)
        follow_up = cls.check_missing_information(device, text)

        is_emergency = hazard is not None

        return {
            "device_type": device or "general_av",
            "symptoms": symptoms,
            "urgency": "Urgent" if is_emergency else urgency,
            "is_safety_hazard": is_emergency,
            "hazard_details": hazard,
            "extracted_room": room_candidate,
            "follow_up_prompt": follow_up if not is_emergency else None,
        }

