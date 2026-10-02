import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.logging_config import logger
from app.pipeline import voice_pipeline
from app.state import session_manager
from app.llm.deepseek import deepseek_client

app = FastAPI(
    title="Business Loan Qualification Voice Agent",
    description="Part 1 Voice Pipeline with DeepSeek LLM, Edge-TTS, and Web Softphone",
    version="0.1.0",
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure required directories exist
settings.ensure_directories()

# Mount Static Files and Audio Recordings
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/recordings", StaticFiles(directory=str(settings.recordings_dir)), name="recordings")

# Mount Question 2 Enterprise Knowledge Retrieval Router
from q2.api import retrieval_router
app.include_router(retrieval_router)

# Mount Question 3 Philippines Voice Bot Router
from q3.api.ph_router import ph_router
app.include_router(ph_router)

# Mount Question 3 Indonesia Voice Bot Router
from q3.api.id_router import id_router
app.include_router(id_router)

# Mount Question 4 Live Insights & Nudges Router
from q4.api import q4_router
app.include_router(q4_router)


# =====================================================================
# Request / Response Schemas
# =====================================================================
class CallStartRequest(BaseModel):
    caller_id: Optional[str] = "web_caller"


class CallTurnRequest(BaseModel):
    call_id: str
    user_text: str
    client_asr_duration_ms: Optional[float] = 0.0
    confidence: Optional[float] = 1.0


class CallEndRequest(BaseModel):
    call_id: str
    reason: Optional[str] = "user_hangup"


# =====================================================================
# HTTP Endpoints
# =====================================================================
@app.get("/")
async def get_index():
    """Serves the main Voice Softphone Web Interface."""
    index_file = static_dir / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Index page not found")
    return FileResponse(str(index_file))


@app.get("/dashboard")
async def get_agent_dashboard():
    """Serves the Q4 Real-Time Agent Copilot & Live Nudges Dashboard."""
    dashboard_file = Path(__file__).parent.parent / "dashboard" / "index.html"
    if not dashboard_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard page not found")
    return FileResponse(str(dashboard_file))



@app.get("/api/health")
async def health_check():
    """System diagnostic and provider readiness check."""
    has_deepseek_key = bool(settings.deepseek_api_key and not settings.deepseek_api_key.startswith("your_"))

    return {
        "status": "healthy",
        "environment": settings.environment,
        "providers": {
            "llm": {
                "configured_provider": "deepseek",
                "model": settings.deepseek_model,
                "api_key_configured": has_deepseek_key,
                "last_error": deepseek_client.last_error,
                "fallback_enabled": settings.llm_fallback_on_error,
            },
            "tts": {
                "provider": settings.tts_provider,
                "voice": settings.tts_voice,
                "rate": settings.tts_rate,
            },
            "asr": {
                "provider": settings.asr_provider,
                "language": settings.asr_language,
            },
        },
        "storage": {
            "recordings_dir": str(settings.recordings_dir),
            "transcripts_dir": str(settings.transcripts_dir),
            "logs_dir": str(settings.logs_dir),
        },
    }


@app.post("/api/call/start")
async def start_call(req: CallStartRequest):
    """Starts a new voice call, generates opening turn and audio."""
    call_id = f"call_{uuid.uuid4().hex[:8]}"
    result = await voice_pipeline.initialize_call(call_id=call_id, caller_id=req.caller_id or "web_caller")
    return JSONResponse(result)


@app.post("/api/call/turn")
async def process_turn(req: CallTurnRequest):
    """Receives customer utterance and returns AI voice agent response."""
    if not req.user_text.strip():
        raise HTTPException(status_code=400, detail="Utterance text cannot be empty")

    result = await voice_pipeline.process_user_speech(
        call_id=req.call_id,
        user_text=req.user_text,
        client_asr_duration_ms=req.client_asr_duration_ms,
        confidence=req.confidence,
    )
    return JSONResponse(result)


@app.post("/api/call/end")
async def end_call(req: CallEndRequest):
    """Hangs up a call session and writes out transcripts and metrics."""
    result = voice_pipeline.end_call(call_id=req.call_id, reason=req.reason or "user_hangup")
    return JSONResponse(result)


@app.get("/api/call/{call_id}/transcript")
async def get_transcript(call_id: str):
    """Retrieves stored JSON transcript for a specific call."""
    session = session_manager.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail="Call session not found")
    return JSONResponse(session.model_dump())


@app.get("/api/calls")
async def list_calls():
    """Lists all recent calls with summary latency and turn metrics."""
    calls = session_manager.list_sessions()
    return JSONResponse({"calls": calls})


@app.get("/api/kb/search")
async def search_kb(query: Optional[str] = None, q: Optional[str] = None):
    """Searches the Darwix knowledge base and returns citations and voice answers."""
    search_query = (query or q or "").strip()
    if not search_query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    from app.kb.retriever import retriever
    resp = retriever.query_with_fallback(search_query)
    return JSONResponse(resp.model_dump())


@app.get("/api/kb/chunks")
async def list_kb_chunks():
    """Lists all loaded knowledge base chunks for verification and auditing."""
    from app.kb.retriever import retriever
    return JSONResponse({
        "total_chunks": len(retriever.chunks),
        "chunks": [c.model_dump() for c in retriever.chunks],
    })


# =====================================================================
# WebSocket Real-Time Voice Connection
# =====================================================================
@app.websocket("/ws/call/{call_id}")
async def websocket_call(websocket: WebSocket, call_id: str):
    """
    Bi-directional streaming WebSocket for zero-overhead real-time voice sessions.
    """
    await websocket.accept()
    logger.info("[WS] WebSocket connected for call %s", call_id)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "start":
                caller_id = data.get("caller_id", "web_caller")
                result = await voice_pipeline.initialize_call(call_id=call_id, caller_id=caller_id)
                await websocket.send_json({
                    "event": "agent_turn",
                    "data": result,
                })

            elif event == "user_speech":
                text = data.get("text", "")
                if text.strip():
                    asr_duration = data.get("asr_duration_ms", 0.0)
                    confidence = data.get("confidence", 1.0)
                    result = await voice_pipeline.process_user_speech(
                        call_id=call_id,
                        user_text=text,
                        client_asr_duration_ms=asr_duration,
                        confidence=confidence,
                    )
                    await websocket.send_json({
                        "event": "agent_turn",
                        "data": result,
                    })

            elif event == "hangup":
                reason = data.get("reason", "caller_hangup")
                metrics = voice_pipeline.end_call(call_id=call_id, reason=reason)
                await websocket.send_json({
                    "event": "call_ended",
                    "data": metrics,
                })
                break

    except WebSocketDisconnect:
        logger.info("[WS] Client disconnected from call %s", call_id)
        voice_pipeline.end_call(call_id=call_id, reason="client_disconnect")
    except Exception as exc:
        logger.error("[WS] Error in websocket for call %s: %s", call_id, exc)
        await websocket.close()
