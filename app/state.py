import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from app.config import settings
from app.logging_config import logger
from app.qualification.models import LoanApplication


class LatencyBreakdown(BaseModel):
    asr_ms: float = 0.0
    llm_ms: float = 0.0
    tts_ms: float = 0.0
    total_roundtrip_ms: float = 0.0


class CallTurn(BaseModel):
    turn_id: int
    speaker: str  # "customer", "agent", "system"
    text: str
    audio_url: Optional[str] = None
    audio_path: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latencies: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    kb_citation: Optional[str] = None


class CallSession(BaseModel):
    call_id: str
    caller_id: str = "web_user"
    status: str = "initialized"  # "initialized", "in-progress", "completed", "escalated", "failed"
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time: Optional[str] = None
    turns: List[CallTurn] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    loan_application: LoanApplication = Field(default_factory=LoanApplication)

    def add_turn(
        self,
        speaker: str,
        text: str,
        audio_url: Optional[str] = None,
        audio_path: Optional[str] = None,
        latencies: Optional[LatencyBreakdown] = None,
        kb_citation: Optional[str] = None,
    ) -> CallTurn:
        turn_id = len(self.turns) + 1
        turn = CallTurn(
            turn_id=turn_id,
            speaker=speaker,
            text=text,
            audio_url=audio_url,
            audio_path=audio_path,
            latencies=latencies or LatencyBreakdown(),
            kb_citation=kb_citation,
        )
        self.turns.append(turn)
        logger.info(
            "[STATE] Call %s - Turn %d recorded | Speaker: %s | Text: '%s' | Total latency: %.1fms",
            self.call_id,
            turn_id,
            speaker,
            text[:60] + ("..." if len(text) > 60 else ""),
            turn.latencies.total_roundtrip_ms,
        )
        return turn

    def get_llm_messages(self, system_prompt: str) -> List[Dict[str, str]]:
        """Formats the conversation history for OpenAI/DeepSeek chat completion format."""
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for turn in self.turns:
            if turn.speaker == "customer":
                messages.append({"role": "user", "content": turn.text})
            elif turn.speaker == "agent":
                messages.append({"role": "assistant", "content": turn.text})
        return messages

    def complete_call(self, status: str = "completed"):
        self.status = status
        self.end_time = datetime.now(timezone.utc).isoformat()
        logger.info("[STATE] Call %s finalized with status: %s", self.call_id, status)
        if settings.save_transcripts:
            self.save_transcript()

    def get_summary_metrics(self) -> Dict[str, Any]:
        customer_turns = [t for t in self.turns if t.speaker == "customer"]
        agent_turns = [t for t in self.turns if t.speaker == "agent"]

        roundtrip_times = [
            t.latencies.total_roundtrip_ms for t in agent_turns if t.latencies.total_roundtrip_ms > 0
        ]
        llm_times = [t.latencies.llm_ms for t in agent_turns if t.latencies.llm_ms > 0]
        tts_times = [t.latencies.tts_ms for t in agent_turns if t.latencies.tts_ms > 0]

        return {
            "call_id": self.call_id,
            "status": self.status,
            "total_turns": len(self.turns),
            "customer_turns": len(customer_turns),
            "agent_turns": len(agent_turns),
            "avg_roundtrip_latency_ms": round(sum(roundtrip_times) / len(roundtrip_times), 1)
            if roundtrip_times
            else 0.0,
            "avg_llm_latency_ms": round(sum(llm_times) / len(llm_times), 1) if llm_times else 0.0,
            "avg_tts_latency_ms": round(sum(tts_times) / len(tts_times), 1) if tts_times else 0.0,
            "loan_application": self.loan_application.get_summary_dict(),
        }

    def save_transcript(self):
        """Saves both machine-readable JSON and human-readable text transcripts."""
        settings.ensure_directories()
        json_path = settings.transcripts_dir / f"{self.call_id}.json"
        txt_path = settings.transcripts_dir / f"{self.call_id}.txt"

        # 1. JSON Transcript
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

        # 2. Text Transcript
        lines = [
            f"=== CALL TRANSCRIPT: {self.call_id} ===",
            f"Caller: {self.caller_id}",
            f"Status: {self.status}",
            f"Start: {self.start_time}",
            f"End: {self.end_time or 'N/A'}",
            "-" * 50,
            "QUALIFICATION SUMMARY:",
            f"  Customer Name:    {self.loan_application.customer_name or 'N/A'}",
            f"  Business Name:    {self.loan_application.business_name or 'N/A'}",
            f"  Business Type:    {self.loan_application.business_type or 'N/A'}",
            f"  Business Age:     {self.loan_application.business_age_raw or (str(self.loan_application.business_age_months) + ' mos' if self.loan_application.business_age_months else 'N/A')}",
            f"  Monthly Revenue:  {self.loan_application.monthly_revenue_raw or ('$' + str(self.loan_application.monthly_revenue) if self.loan_application.monthly_revenue else 'N/A')}",
            f"  Requested Amount: {self.loan_application.requested_amount_raw or ('$' + str(self.loan_application.requested_amount) if self.loan_application.requested_amount else 'N/A')}",
            f"  Loan Purpose:     {self.loan_application.loan_purpose or 'N/A'}",
            f"  Existing Debt:    {'Yes' if self.loan_application.has_existing_loans is True else ('No' if self.loan_application.has_existing_loans is False else 'N/A')}",
            f"  Location:         {self.loan_application.location or 'N/A'}",
            f"  Fields Collected: {self.loan_application.get_collected_count()} / 9",
            f"  Escalated:        {self.loan_application.is_escalated} ({self.loan_application.escalation_reason or 'None'})",
            "-" * 50,
        ]
        for turn in self.turns:
            speaker_tag = "CUSTOMER" if turn.speaker == "customer" else "AGENT"
            latency_str = f" [Latency: {turn.latencies.total_roundtrip_ms:.0f}ms]" if turn.latencies.total_roundtrip_ms > 0 else ""
            citation_str = f" [KB Source: {turn.kb_citation}]" if turn.kb_citation else ""
            lines.append(f"[{turn.timestamp[11:19]}] {speaker_tag}{latency_str}{citation_str}: {turn.text}")
        lines.append("-" * 50)
        metrics = self.get_summary_metrics()
        lines.append(f"Summary: {metrics['total_turns']} turns | Avg Turnaround: {metrics['avg_roundtrip_latency_ms']}ms")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        logger.info("[STATE] Saved transcripts to %s and %s", json_path.name, txt_path.name)


class SessionManager:
    """In-memory active session manager with disk persistence."""

    def __init__(self):
        self._sessions: Dict[str, CallSession] = {}

    def create_session(self, call_id: str, caller_id: str = "web_user") -> CallSession:
        session = CallSession(call_id=call_id, caller_id=caller_id, status="in-progress")
        self._sessions[call_id] = session
        logger.info("[STATE] Created new call session %s for %s", call_id, caller_id)
        return session

    def get_session(self, call_id: str) -> Optional[CallSession]:
        if call_id in self._sessions:
            return self._sessions[call_id]

        # Attempt to load from saved transcript if exists
        json_path = settings.transcripts_dir / f"{call_id}.json"
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    session = CallSession.model_validate(data)
                    self._sessions[call_id] = session
                    return session
            except Exception as e:
                logger.error("[STATE] Error loading session %s from disk: %s", call_id, e)
        return None

    def list_sessions(self) -> List[Dict[str, Any]]:
        # Collect active and stored sessions
        session_summaries = []
        seen_ids = set()

        for s in self._sessions.values():
            session_summaries.append(s.get_summary_metrics())
            seen_ids.add(s.call_id)

        # Check saved transcripts on disk
        if settings.transcripts_dir.exists():
            for p in sorted(settings.transcripts_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                call_id = p.stem
                if call_id not in seen_ids:
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            sess = CallSession.model_validate(data)
                            session_summaries.append(sess.get_summary_metrics())
                            seen_ids.add(call_id)
                    except Exception:
                        pass

        return session_summaries


session_manager = SessionManager()
