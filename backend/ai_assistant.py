"""AI Reasoning & Guided Troubleshooting Assistant.

Integrates RAG knowledge retrieval with a Hybrid Expert Rule Engine.
If an external LLM API key (OpenAI or Gemini) is supplied, it provides generative reasoning.
Otherwise, it executes an empirical Rule-Based Expert System built directly from the
5,000-case dataset, guaranteeing full local functionality with zero external API dependencies.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .config import settings
from .dataset_loader import AVDatasetLoader
from .knowledge_base import retriever

logger = logging.getLogger(__name__)


class AIAssistant:
    """Intelligent troubleshooting assistant providing guided diagnostic workflows."""

    def __init__(self, loader: Optional[AVDatasetLoader] = None):
        self.loader = loader or AVDatasetLoader()
        self.retriever = retriever

    def analyze_and_plan(
        self,
        device_type: str,
        symptom: str,
        room_no: str,
        model: Optional[str] = None,
        power_status: str = "unknown",
        input_source: str = "unknown",
        cable_status: str = "unknown",
    ) -> Dict[str, Any]:
        """Perform comprehensive symptom analysis and synthesize an action plan.

        Returns:
            Structured diagnostic plan containing:
            - root_cause_hypotheses
            - historical_resolution_rate
            - escalation_risk_level ('Low', 'Medium', 'High')
            - step_by_step_plan (ordered list of troubleshooting steps)
            - retrieved_knowledge_context
            - reasoning_mode ('llm' or 'rule_based_expert')
        """
        # 1. Empirical Historical Match
        empirical = self.loader.diagnose_symptom(
            symptom=symptom,
            device_type=device_type,
            model=model if model and model != "unknown" else None,
            power_status=power_status if power_status and power_status != "unknown" else None,
            cable_status=cable_status if cable_status and cable_status != "unknown" else None,
        )

        # 2. RAG Knowledge Retrieval
        rag_query = f"{device_type} {symptom} power:{power_status} cable:{cable_status} input:{input_source}"
        retrieved_docs = self.retriever.retrieve(rag_query, device_type=device_type, top_k=4)

        # 3. Determine Escalation Risk Level
        esc_rate = empirical.get("historical_escalation_rate_pct", 30.0)
        if esc_rate >= 50.0 or power_status == "off" and cable_status == "disconnected":
            risk_level = "High"
            priority = "High"
        elif esc_rate >= 25.0:
            risk_level = "Medium"
            priority = "Medium"
        else:
            risk_level = "Low"
            priority = "Normal"

        # 4. Synthesize Ordered Troubleshooting Steps
        steps: List[str] = []

        # Environmental Pre-checks
        if cable_status == "loose":
            steps.append("Firmly reseat all video/audio cables without forcing connectors.")
        elif cable_status == "disconnected":
            steps.append("Check physical cable connection to the wall port and device interface.")

        if power_status == "off":
            steps.append("Verify the main power switch on the wall socket and press the hardware power button.")
        elif power_status == "standby":
            steps.append("Take the device out of standby mode using the remote control or front control panel.")

        # Add empirical recommended fix steps from dataset
        for fix_data in empirical.get("recommended_fix_steps", []):
            fix_text = fix_data["fix_step"].strip()
            if fix_text not in steps:
                steps.append(fix_text)

        # Fallback to retrieved RAG fixes if steps are sparse
        if len(steps) < 2:
            for doc in retrieved_docs:
                doc_fix = doc.get("fix_step", "").strip()
                if doc_fix and doc_fix not in steps:
                    steps.append(doc_fix)

        # Standard ultimate fallback step
        if not steps:
            steps.append(f"Perform a safe soft reboot of the {device_type.replace('_', ' ')}.")
            steps.append("Check input channel alignment and connection cables.")

        # Always add final escalation step
        steps.append(f"If the issue persists, escalate for physical hardware inspection in room {room_no}.")

        # 5. AI Reasoning Generation (LLM or Rule-based)
        reasoning_mode = "rule_based_expert"
        ai_summary = ""

        # Try OpenAI LLM if configured
        if settings.OPENAI_API_KEY:
            ai_summary = self._call_openai_reasoning(
                device_type, symptom, room_no, power_status, cable_status, input_source, steps, retrieved_docs
            )
            if ai_summary:
                reasoning_mode = "llm_openai"

        # Try Gemini LLM if configured and OpenAI wasn't used
        if not ai_summary and settings.GEMINI_API_KEY:
            ai_summary = self._call_gemini_reasoning(
                device_type, symptom, room_no, power_status, cable_status, input_source, steps, retrieved_docs
            )
            if ai_summary:
                reasoning_mode = "llm_gemini"

        if not ai_summary:
            # Rule-based empirical synthesis (zero external API dependency)
            res_rate = empirical.get("historical_resolution_rate_pct", 65.0)
            ai_summary = (
                f"Empirical Diagnostic Evaluation for {device_type.replace('_', ' ').title()} in Room {room_no}:\n"
                f"Observed symptom: '{symptom}' under power state '{power_status}' and cable seating '{cable_status}'.\n"
                f"Analysis of similar historical classroom incidents shows an empirical {res_rate}% first-touch resolution rate.\n"
                f"[Source: Internal Historical AV Incidents Log — Note: These are empirical past resolutions, not official manufacturer manual instructions.]\n"
                f"Proceed through the guided steps below, confirming after each step whether the issue is resolved."
            )

        return {
            "device_type": device_type,
            "symptom": symptom,
            "room_no": room_no,
            "model": model,
            "power_status": power_status,
            "cable_status": cable_status,
            "input_source": input_source,
            "historical_resolution_rate_pct": empirical.get("historical_resolution_rate_pct", 65.0),
            "historical_escalation_rate_pct": esc_rate,
            "escalation_risk_level": risk_level,
            "ticket_priority": priority,
            "matched_historical_cases": empirical.get("matched_records_count", 0),
            "troubleshooting_steps": steps,
            "ai_reasoning_summary": ai_summary,
            "reasoning_mode": reasoning_mode,
            "attribution": "Empirical historical classroom incident record (Internal AV Log Dataset) - Not official manufacturer manual instructions",
            "retrieved_context_documents": [
                {
                    "title": f"{doc.get('device_type')} - {doc.get('symptom')}",
                    "model": doc.get("model"),
                    "fix": doc.get("fix_step"),
                    "resolution_rate": doc.get("resolution_rate_pct"),
                    "historical_total": doc.get("historical_total"),
                    "similarity": doc.get("similarity_score", 1.0),
                    "attribution": doc.get("attribution"),
                }
                for doc in retrieved_docs[:4]
            ],
        }

    def _call_openai_reasoning(
        self,
        device_type: str,
        symptom: str,
        room_no: str,
        power_status: str,
        cable_status: str,
        input_source: str,
        steps: List[str],
        docs: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Optional OpenAI completion call strictly grounded in retrieved records."""
        try:
            import json
            import urllib.request

            context_str = "\n".join(
                f"- [Historical Record] Device: {d.get('device_type')} ({d.get('model')}) | Symptom: {d.get('symptom')} | Fix: {d.get('fix_step')} ({d.get('resolution_rate_pct')}% resolved)"
                for d in docs[:4]
            )

            prompt = (
                f"You are an AI Smart Classroom AV Troubleshooting Assistant.\n"
                f"CRITICAL GROUNDING RULES:\n"
                f"1. Base your explanation strictly on the retrieved historical classroom incidents below.\n"
                f"2. NEVER invent manual citations or claim retrieved examples are official manufacturer instructions.\n"
                f"3. Explain that guidance reflects empirical classroom troubleshooting history.\n\n"
                f"Incident Context:\n"
                f"Room: {room_no} | Device: {device_type} | Symptom: {symptom} | Power: {power_status} | Cable: {cable_status} | Input: {input_source}\n\n"
                f"Retrieved Historical Records:\n{context_str}\n\n"
                f"Planned Steps:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)) + "\n\n"
                f"Provide a concise, 2-3 sentence grounded explanation and confirm each step should be tested one-by-one."
            )

            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps({
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 180,
                }).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                },
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.debug("Optional OpenAI call skipped/failed: %s", e)
            return None

    def _call_gemini_reasoning(
        self,
        device_type: str,
        symptom: str,
        room_no: str,
        power_status: str,
        cable_status: str,
        input_source: str,
        steps: List[str],
        docs: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Optional Google Gemini completion call strictly grounded in retrieved records."""
        try:
            import json
            import urllib.request

            context_str = "\n".join(
                f"- [Historical Record] Device: {d.get('device_type')} | Symptom: {d.get('symptom')} | Fix: {d.get('fix_step')}"
                for d in docs[:4]
            )

            prompt = (
                f"You are an AI Smart Classroom AV Troubleshooting Assistant.\n"
                f"CRITICAL GROUNDING RULES:\n"
                f"1. Base your explanation strictly on the retrieved historical classroom incidents below.\n"
                f"2. NEVER invent manual citations or claim retrieved examples are official manufacturer instructions.\n"
                f"3. Explain that guidance reflects empirical classroom troubleshooting history.\n\n"
                f"Incident Context:\n"
                f"Room: {room_no} | Device: {device_type} | Symptom: {symptom} | Power: {power_status} | Cable: {cable_status}\n\n"
                f"Retrieved Historical Records:\n{context_str}\n\n"
                f"Provide a concise, 2-3 sentence grounded explanation."
            )

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
            body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.debug("Optional Gemini call skipped/failed: %s", e)
            return None


assistant = AIAssistant()
