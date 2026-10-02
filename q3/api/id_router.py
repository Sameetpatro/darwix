from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from pathlib import Path
import time

from q3.indonesia.agent import id_voice_agent
from q3.indonesia.dialog_manager import id_dialog_manager
from app.config import settings

id_router = APIRouter(prefix="/id", tags=["Indonesia Voice Bot"])

ID_RECORDINGS_DIR = settings.recordings_dir / "indonesia"
ID_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


class IDStartCallRequest(BaseModel):
    session_id: Optional[str] = None
    dialect_style: Optional[str] = "colloquial"


class IDTurnRequest(BaseModel):
    session_id: str
    utterance: str
    synthesize_audio: Optional[bool] = True


@id_router.post("/call/start")
def start_id_call(req: IDStartCallRequest):
    session_id = req.session_id or f"id_{int(time.time() * 1000)}"
    res = id_voice_agent.start_call(session_id, req.dialect_style or "colloquial")
    return res


@id_router.post("/call/turn")
async def process_id_turn(req: IDTurnRequest):
    if not req.utterance.strip():
        raise HTTPException(status_code=400, detail="Utterance cannot be empty")
    res = await id_voice_agent.handle_turn(
        session_id=req.session_id,
        user_utterance=req.utterance,
        synthesize_audio=req.synthesize_audio
    )
    return res


@id_router.get("/call/context/{session_id}")
def get_id_context(session_id: str):
    session = id_dialog_manager.get_or_create_session(session_id)
    return {
        "session_id": session_id,
        "language": session.language,
        "dialect_style": session.dialect_style,
        "escalated": session.escalated,
        "support_path_offered": session.support_path_offered,
        "account_context": session.account_context.model_dump(),
        "turn_count": len(session.turns)
    }


@id_router.get("/audio/{filename}")
def get_id_audio(filename: str):
    file_path = ID_RECORDINGS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(path=str(file_path), media_type="audio/mpeg")
