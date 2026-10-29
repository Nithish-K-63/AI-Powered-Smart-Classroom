"""Persistence repository layer for Smart Classroom AV Assistant.

Provides seamless storage of live user complaints and technician escalation tickets.
Automatically connects to MongoDB if available, with an automatic resilient local
JSON persistence fallback when MongoDB is unavailable or unconfigured.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import settings

logger = logging.getLogger(__name__)


class RepositoryManager:
    """Manages complaint and ticket persistence with dynamic MongoDB/Local fallback."""

    def __init__(
        self,
        mongodb_uri: Optional[str] = None,
        db_name: Optional[str] = None,
        local_store_path: Optional[Path] = None,
    ):
        self.mongodb_uri = mongodb_uri or settings.MONGODB_URI
        self.db_name = db_name or settings.MONGODB_DB_NAME
        self.local_store_path = local_store_path or settings.LOCAL_STORE_PATH

        self._lock = threading.Lock()
        self.mongo_client = None
        self.db = None
        self.backend_type: str = "local_json"
        self.is_fallback: bool = True

        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Attempt connection to MongoDB; gracefully fall back to local JSON store."""
        try:
            import pymongo
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

            logger.info("Testing MongoDB connection to: %s", self.mongodb_uri)
            client = pymongo.MongoClient(
                self.mongodb_uri,
                serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            )
            # Test ping
            client.admin.command("ping")
            self.mongo_client = client
            self.db = client[self.db_name]
            self.backend_type = "mongodb"
            self.is_fallback = False
            logger.info("Successfully connected to MongoDB database '%s'", self.db_name)

            # Ensure indexes
            self.db["complaints"].create_index("complaint_id", unique=True)
            self.db["tickets"].create_index("ticket_id", unique=True)
            self.db["complaints"].create_index("room_no")
            self.db["complaints"].create_index("device_type")
            return
        except Exception as e:
            logger.warning(
                "MongoDB not available (%s). Activating local resilient JSON store at '%s'",
                e,
                self.local_store_path,
            )
            self.backend_type = "local_json"
            self.is_fallback = True
            self._ensure_local_store()

    def _ensure_local_store(self) -> None:
        """Ensure the local JSON database file and parent directory exist."""
        self.local_store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.local_store_path.exists():
            with open(self.local_store_path, "w", encoding="utf-8") as f:
                json.dump({"complaints": [], "tickets": []}, f, indent=2)

    def _read_local_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Thread-safe read from local JSON storage."""
        with self._lock:
            self._ensure_local_store()
            try:
                with open(self.local_store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error("Error reading local store: %s", e)
                return {"complaints": [], "tickets": []}

    def _write_local_data(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """Thread-safe write to local JSON storage."""
        with self._lock:
            temp_path = self.local_store_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            temp_path.replace(self.local_store_path)

    # -------------------------------------------------------------
    # Complaint Operations
    # -------------------------------------------------------------
    def create_complaint(self, complaint: Dict[str, Any]) -> Dict[str, Any]:
        """Save a new complaint record."""
        now = datetime.now(timezone.utc).isoformat()
        complaint.setdefault("created_at", now)
        complaint.setdefault("updated_at", now)
        complaint.setdefault("status", "active")
        complaint.setdefault("attempted_fixes", [])
        complaint["source"] = "live_mongodb" if not self.is_fallback else "live_local_store"
        complaint["is_historical"] = False

        if self.backend_type == "mongodb" and self.db is not None:
            doc = dict(complaint)
            self.db["complaints"].insert_one(doc)
            doc.pop("_id", None)
            return doc
        else:
            data = self._read_local_data()
            data["complaints"].append(complaint)
            self._write_local_data(data)
            return complaint

    def get_complaint(self, complaint_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a complaint by its ID."""
        if self.backend_type == "mongodb" and self.db is not None:
            doc = self.db["complaints"].find_one({"complaint_id": complaint_id})
            if doc:
                doc.pop("_id", None)
            return doc
        else:
            data = self._read_local_data()
            for c in data["complaints"]:
                if c.get("complaint_id") == complaint_id:
                    return c
            return None

    def list_complaints(
        self,
        device_type: Optional[str] = None,
        room_no: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List complaints with optional filters."""
        if self.backend_type == "mongodb" and self.db is not None:
            query: Dict[str, Any] = {}
            if device_type:
                query["device_type"] = device_type
            if room_no:
                query["room_no"] = room_no
            if status:
                query["status"] = status
            cursor = self.db["complaints"].find(query).sort("created_at", -1).limit(limit)
            results = []
            for doc in cursor:
                doc.pop("_id", None)
                results.append(doc)
            return results
        else:
            data = self._read_local_data()
            results = data["complaints"]
            if device_type:
                results = [c for c in results if c.get("device_type") == device_type]
            if room_no:
                results = [c for c in results if c.get("room_no") == room_no]
            if status:
                results = [c for c in results if c.get("status") == status]
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return results[:limit]

    def update_complaint(self, complaint_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields in an existing complaint."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self.backend_type == "mongodb" and self.db is not None:
            self.db["complaints"].update_one({"complaint_id": complaint_id}, {"$set": updates})
            return self.get_complaint(complaint_id)
        else:
            data = self._read_local_data()
            for c in data["complaints"]:
                if c.get("complaint_id") == complaint_id:
                    c.update(updates)
                    self._write_local_data(data)
                    return c
            return None

    def add_attempted_fix(
        self,
        complaint_id: str,
        fix_step: str,
        resolved: bool,
    ) -> Optional[Dict[str, Any]]:
        """Log an attempted troubleshooting fix step against a complaint."""
        now = datetime.now(timezone.utc).isoformat()
        fix_entry = {
            "step": fix_step,
            "resolved": resolved,
            "timestamp": now,
        }

        if self.backend_type == "mongodb" and self.db is not None:
            self.db["complaints"].update_one(
                {"complaint_id": complaint_id},
                {
                    "$push": {"attempted_fixes": fix_entry},
                    "$set": {
                        "updated_at": now,
                        "status": "resolved" if resolved else "active",
                    },
                },
            )
            return self.get_complaint(complaint_id)
        else:
            data = self._read_local_data()
            for c in data["complaints"]:
                if c.get("complaint_id") == complaint_id:
                    c.setdefault("attempted_fixes", []).append(fix_entry)
                    c["updated_at"] = now
                    if resolved:
                        c["status"] = "resolved"
                    self._write_local_data(data)
                    return c
            return None

    # -------------------------------------------------------------
    # Escalation Ticket Operations
    # -------------------------------------------------------------
    def create_ticket(self, ticket: Dict[str, Any]) -> Dict[str, Any]:
        """Create a technician escalation ticket."""
        now = datetime.now(timezone.utc).isoformat()
        ticket.setdefault("created_at", now)
        ticket.setdefault("updated_at", now)
        ticket.setdefault("status", "Pending Technician")
        ticket.setdefault("technician_notes", "")
        ticket["source"] = "live_mongodb" if not self.is_fallback else "live_local_store"

        # Also update the associated complaint status to 'escalated'
        complaint_id = ticket.get("complaint_id")
        if complaint_id:
            self.update_complaint(
                complaint_id,
                {"status": "escalated", "ticket_id": ticket.get("ticket_id")},
            )

        if self.backend_type == "mongodb" and self.db is not None:
            doc = dict(ticket)
            self.db["tickets"].insert_one(doc)
            doc.pop("_id", None)
            return doc
        else:
            data = self._read_local_data()
            data["tickets"].append(ticket)
            self._write_local_data(data)
            return ticket

    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an escalation ticket by its ID."""
        if self.backend_type == "mongodb" and self.db is not None:
            doc = self.db["tickets"].find_one({"ticket_id": ticket_id})
            if doc:
                doc.pop("_id", None)
            return doc
        else:
            data = self._read_local_data()
            for t in data["tickets"]:
                if t.get("ticket_id") == ticket_id:
                    return t
            return None

    def list_tickets(
        self,
        status: Optional[str] = None,
        device_type: Optional[str] = None,
        room_no: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List escalation tickets with optional filters."""
        if self.backend_type == "mongodb" and self.db is not None:
            query: Dict[str, Any] = {}
            if status:
                query["status"] = status
            if device_type:
                query["device_type"] = device_type
            if room_no:
                query["room_no"] = room_no
            cursor = self.db["tickets"].find(query).sort("created_at", -1).limit(limit)
            results = []
            for doc in cursor:
                doc.pop("_id", None)
                results.append(doc)
            return results
        else:
            data = self._read_local_data()
            results = data["tickets"]
            if status:
                results = [t for t in results if t.get("status") == status]
            if device_type:
                results = [t for t in results if t.get("device_type") == device_type]
            if room_no:
                results = [t for t in results if t.get("room_no") == room_no]
            results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return results[:limit]

    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update technician status or notes on an escalation ticket."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self.backend_type == "mongodb" and self.db is not None:
            self.db["tickets"].update_one({"ticket_id": ticket_id}, {"$set": updates})
            return self.get_ticket(ticket_id)
        else:
            data = self._read_local_data()
            for t in data["tickets"]:
                if t.get("ticket_id") == ticket_id:
                    t.update(updates)
                    self._write_local_data(data)
                    return t
            return None

    def get_storage_status(self) -> Dict[str, Any]:
        """Return connectivity status of the persistence layer."""
        data = self._read_local_data() if self.is_fallback else None
        complaint_count = (
            self.db["complaints"].count_documents({})
            if self.backend_type == "mongodb" and self.db is not None
            else len(data.get("complaints", [])) if data else 0
        )
        ticket_count = (
            self.db["tickets"].count_documents({})
            if self.backend_type == "mongodb" and self.db is not None
            else len(data.get("tickets", [])) if data else 0
        )

        return {
            "backend_type": self.backend_type,
            "is_fallback": self.is_fallback,
            "connected_database": self.db_name if not self.is_fallback else "Local JSON File",
            "storage_path": str(self.local_store_path) if self.is_fallback else self.mongodb_uri,
            "total_live_complaints": complaint_count,
            "total_tickets": ticket_count,
        }


# Global repository instance
repository = RepositoryManager()
