"""Classroom QR Code Generation and Scanning Service.

Generates safe, opaque tokens for classrooms and resolves them without exposing
credentials, passwords, or technician details in the QR code payload.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any, Dict, Optional

import qrcode
from PIL import Image

logger = logging.getLogger(__name__)


class QRService:
    """Manages generation of classroom QR codes and camera/image decoding."""

    @classmethod
    def generate_classroom_qr_image(
        cls,
        classroom_id: str,
        qr_token: str,
        base_url: str = "http://localhost:8501",
    ) -> Image.Image:
        """Generate QR code PIL Image for a classroom."""
        # Safe URL encoding: contains only the classroom token and action
        payload = f"{base_url}/?action=scan_qr&room_token={qr_token}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1E3A8A", back_color="white")
        return img.convert("RGB")

    @classmethod
    def generate_qr_base64(cls, classroom_id: str, qr_token: str) -> str:
        """Generate base64 encoded PNG data URI for embedding in HTML/Streamlit."""
        img = cls.generate_classroom_qr_image(classroom_id, qr_token)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

    @classmethod
    def decode_qr_image(cls, image_bytes: bytes) -> Optional[str]:
        """Decode QR token from uploaded image bytes or camera input."""
        try:
            import cv2
            import numpy as np

            # Decode using OpenCV WeChat / QR detector
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                detector = cv2.QRCodeDetector()
                data, bbox, _ = detector.detectAndDecode(img)
                if data:
                    # Extract room_token if it is a URL or return raw token
                    if "room_token=" in data:
                        token = data.split("room_token=")[-1].split("&")[0]
                        return token
                    return data
        except Exception as e:
            logger.warning("OpenCV QR decoding encounter: %s", e)

        # Fallback: pyzbar if available
        try:
            from pyzbar.pyzbar import decode
            img = Image.open(io.BytesIO(image_bytes))
            decoded = decode(img)
            if decoded:
                data = decoded[0].data.decode("utf-8")
                if "room_token=" in data:
                    return data.split("room_token=")[-1].split("&")[0]
                return data
        except Exception:
            pass

        return None


qr_service = QRService()

