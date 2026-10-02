from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from pathlib import Path
import time

from q3.philippines.agent import ph_voice_agent
from q3.philippines.dialog_manager import ph_dialog_manager
from app.config import settings

ph_router = APIRouter(prefix="/ph", tags=["Philippines Voice Bot"])

PH_RECORDINGS_DIR = settings.recordings_dir / "philippines"
PH_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class PHStartCallRequest(BaseModel):
    session_id: Optional[str] = None
    language: Optional[str] = "taglish"


class PHTurnRequest(BaseModel):
    session_id: str
    utterance: str
    synthesize_audio: Optional[bool] = True


@ph_router.post("/call/start")
def start_ph_call(req: PHStartCallRequest):
    session_id = req.session_id or f"ph_{int(time.time() * 1000)}"
    res = ph_voice_agent.start_call(session_id, req.language or "taglish")
    return res


@ph_router.post("/call/turn")
async def process_ph_turn(req: PHTurnRequest):
    if not req.utterance.strip():
        raise HTTPException(status_code=400, detail="Utterance cannot be empty")
    res = await ph_voice_agent.handle_turn(
        session_id=req.session_id,
        user_utterance=req.utterance,
        synthesize_audio=req.synthesize_audio
    )
    return res


@ph_router.get("/call/profile/{session_id}")
def get_ph_profile(session_id: str):
    session = ph_dialog_manager.get_or_create_session(session_id)
    return {
        "session_id": session_id,
        "language": session.language,
        "escalated": session.escalated,
        "completed": session.completed,
        "profile": session.profile.model_dump(),
        "missing_slots": session.profile.get_missing_fields(),
        "turn_count": len(session.turns)
    }


@ph_router.get("/audio/{filename}")
def get_ph_audio(filename: str):
    file_path = PH_RECORDINGS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(path=str(file_path), media_type="audio/mpeg")
