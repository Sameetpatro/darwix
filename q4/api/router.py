import asyncio
import time
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from app.logging_config import logger
from q4.audio.streaming import AudioChunk
from q4.audio.replay import RealtimeCallReplayer, SAMPLE_CALLS
from q4.asr.streaming_asr import StreamingASREngine
from q4.conversation.state import LiveCallState
from q4.signals.engine import SignalDetectionEngine
from q4.nudge.engine import NudgeEngine, nudge_engine
from q4.nudge.priority import priority_manager
from q4.nudge.suppression import suppression_engine
from q4.delivery.websocket import ws_delivery_manager

q4_router = APIRouter(prefix="/q4", tags=["Q4 Live Insights & Nudges"])

# Global active sessions registry
active_call_states: Dict[str, LiveCallState] = {}
active_simulation_tasks: Dict[str, asyncio.Task] = {}


class SimulationRequest(BaseModel):
    scenario: str = "call_cross_sell"  # call_cross_sell, call_compliance_gap, call_rising_frustration, call_payment_difficulty, call_false_positive_cross_sell, call_noisy_ambiguous
    time_scale: float = 0.5  # 0.5 = 2x speed for testing; 1.0 = strict real-time wall-clock


class PriorityConfigRequest(BaseModel):
    mapping: Dict[str, str]


class ThresholdConfigRequest(BaseModel):
    min_confidence: float = 0.75
    cooldown_seconds: float = 20.0


# ---------------------------------------------------------------------
# WebSocket Endpoint for Live Agent Dashboard
# ---------------------------------------------------------------------
@q4_router.websocket("/ws")
async def websocket_q4_stream(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket stream delivering:
    - Live streaming transcript deltas (ASR partials & finals)
    - Structured conversation signals
    - In-call nudges with countdown expiration
    - Real-time pipeline latency telemetry (L1..L4)
    """
    await ws_delivery_manager.connect(websocket)
    try:
        # Send initial handshake with current system status
        await websocket.send_json({
            "event": "connected",
            "timestamp": time.time(),
            "message": "Connected to Darwix Q4 Real-Time Nudge Pipeline",
            "config": {
                "min_confidence": suppression_engine.min_confidence_threshold,
                "cooldown_seconds": suppression_engine.cooldown_seconds,
                "priorities": priority_manager.get_mapping(),
            }
        })

        while True:
            # Receive client interactions (e.g. acknowledge nudge, dismiss, ping)
            data = await websocket.receive_json()
            event_type = data.get("action")
            if event_type == "acknowledge_nudge":
                nudge_id = data.get("nudge_id")
                logger.info("[WS_CLIENT] Agent acknowledged nudge %s", nudge_id)
                await ws_delivery_manager.broadcast_event("nudge_acknowledged", {"nudge_id": nudge_id})
            elif event_type == "ping":
                await websocket.send_json({"event": "pong", "timestamp": time.time()})

    except WebSocketDisconnect:
        ws_delivery_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("[WS_ERROR] WebSocket encountered error: %s", exc)
        ws_delivery_manager.disconnect(websocket)


# ---------------------------------------------------------------------
# REST Endpoints for Simulation & Telemetry
# ---------------------------------------------------------------------
@q4_router.post("/simulate")
async def trigger_live_simulation(req: SimulationRequest):
    """
    Triggers an asynchronous real-time call replay through the complete pipeline:
    Audio Replay -> Streaming ASR (L1) -> Signal Extraction (L2) -> Nudge Engine (L3) -> WebSocket Push (L4).
    """
    if req.scenario not in SAMPLE_CALLS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario '{req.scenario}'. Available: {list(SAMPLE_CALLS.keys())}"
        )

    call_id = f"call_{req.scenario}_{int(time.time())}"
    
    # Cancel previous simulation for clean demo if running
    if "current_sim" in active_simulation_tasks and not active_simulation_tasks["current_sim"].done():
        active_simulation_tasks["current_sim"].cancel()

    # Launch background streaming simulation
    task = asyncio.create_task(run_streaming_pipeline(call_id, req.scenario, req.time_scale))
    active_simulation_tasks["current_sim"] = task

    return {
        "status": "started",
        "call_id": call_id,
        "scenario": req.scenario,
        "time_scale": req.time_scale,
        "message": f"Simulating live call '{req.scenario}' in real-time."
    }


async def run_streaming_pipeline(call_id: str, scenario_key: str, time_scale: float = 0.5):
    """Executes the live end-to-end streaming pipeline asynchronously."""
    logger.info("[PIPELINE] Starting live streaming pipeline for call %s (Scenario: %s)", call_id, scenario_key)
    
    replayer = RealtimeCallReplayer(chunk_duration_ms=250.0, time_scale=time_scale)
    from q4.asr.streaming_asr import streaming_asr_engine
    from q4.signals.engine import signal_engine
    call_state = LiveCallState(call_id=call_id)
    active_call_states[call_id] = call_state

    turns_script = SAMPLE_CALLS[scenario_key]

    # Notify dashboard of call start
    await ws_delivery_manager.broadcast_event("call_started", {
        "call_id": call_id,
        "scenario": scenario_key,
        "turns_total": len(turns_script),
        "status": "active"
    })

    try:
        async for chunk in replayer.stream_call(call_id, turns_script):
            # 1. Audio Received -> Streaming ASR
            t_chunk_received = chunk.received_at
            transcript_chunk = streaming_asr_engine.process_chunk(chunk)
            
            # Broadcast live audio & partial transcript to dashboard
            await ws_delivery_manager.broadcast_event("audio_stream", {
                "chunk_id": chunk.chunk_id,
                "speaker": transcript_chunk.speaker,
                "partial_text": transcript_chunk.partial_text,
                "is_final": transcript_chunk.is_final,
                "asr_latency_ms": transcript_chunk.asr_latency_ms
            })

            # 2. Ingest into state and check if turn committed
            finalized_turn = call_state.ingest_transcript_chunk(transcript_chunk)
            if finalized_turn:
                await ws_delivery_manager.broadcast_event("turn_finalized", {
                    "turn_id": finalized_turn.turn_id,
                    "speaker": finalized_turn.speaker,
                    "text": finalized_turn.text,
                    "confidence": finalized_turn.confidence,
                    "stage": call_state.stage
                })

                # 3. Real-Time Signal Extraction (L2)
                signals = signal_engine.process_turn(finalized_turn, call_state)
                for sig in signals:
                    call_state.add_signal(sig)
                    await ws_delivery_manager.broadcast_event("signal_detected", sig.model_dump())

                    # 4. Nudge Engine: Suppression -> Generation (L3)
                    nudge = await nudge_engine.process_signal(sig, call_state, use_deepseek=False)
                    if nudge:
                        # 5. Real-Time WebSocket Delivery (L4)
                        l4_ms = await ws_delivery_manager.broadcast_nudge(nudge)
                        
                        # Calculate total end-to-end latency L_total
                        # L_total = L1 (ASR) + L2 (Signal) + L3 (Nudge Gen) + L4 (Delivery)
                        l1_ms = transcript_chunk.asr_latency_ms
                        l2_ms = sig.detection_latency_ms
                        l3_ms = nudge.generation_latency_ms
                        l_total_ms = round(l1_ms + l2_ms + l3_ms + l4_ms, 2)

                        await ws_delivery_manager.broadcast_event("latency_sample", {
                            "signal_id": sig.signal_id,
                            "nudge_id": nudge.nudge_id,
                            "type": nudge.type,
                            "L1_asr_ms": l1_ms,
                            "L2_signal_ms": l2_ms,
                            "L3_nudge_ms": l3_ms,
                            "L4_delivery_ms": l4_ms,
                            "L_total_ms": l_total_ms
                        })
                    else:
                        # Signal was suppressed
                        await ws_delivery_manager.broadcast_event("signal_suppressed", {
                            "signal_id": sig.signal_id,
                            "type": sig.type,
                            "confidence": sig.confidence,
                            "reason": "Suppressed by Nudge Engine"
                        })

        # Call completed
        call_state.status = "completed"
        await ws_delivery_manager.broadcast_event("call_completed", call_state.get_summary())
        logger.info("[PIPELINE] Completed live streaming call %s", call_id)

    except asyncio.CancelledError:
        logger.info("[PIPELINE] Simulation task cancelled for call %s", call_id)
        call_state.status = "cancelled"
    except Exception as exc:
        logger.error("[PIPELINE] Error during simulation: %s", exc, exc_info=True)


@q4_router.get("/metrics")
async def get_q4_metrics():
    """Returns real-time measured latency percentiles (L1..L4, Ltotal) and suppression counters."""
    from q4.asr.streaming_asr import streaming_asr_engine
    l1_stats = streaming_asr_engine.get_latency_stats()
    from q4.signals.engine import signal_engine
    l2_stats = signal_engine.get_latency_stats()
    l3_stats = nudge_engine.get_latency_stats()
    l4_stats = ws_delivery_manager.get_latency_stats()
    suppression_stats = nudge_engine.get_suppression_stats()

    # Calculate end-to-end total
    mean_total = round(l1_stats.get("mean_ms", 0) + l2_stats.get("mean_ms", 0) + l3_stats.get("mean_ms", 0) + l4_stats.get("mean_ms", 0), 2)
    p50_total = round(l1_stats.get("p50_ms", 0) + l2_stats.get("p50_ms", 0) + l3_stats.get("p50_ms", 0) + l4_stats.get("p50_ms", 0), 2)
    p95_total = round(l1_stats.get("p95_ms", 0) + l2_stats.get("p95_ms", 0) + l3_stats.get("p95_ms", 0) + l4_stats.get("p95_ms", 0), 2)

    return {
        "latencies": {
            "L1_asr": l1_stats,
            "L2_signal_extraction": l2_stats,
            "L3_nudge_generation": l3_stats,
            "L4_delivery": l4_stats,
            "L_total_end_to_end": {
                "mean_ms": mean_total,
                "p50_ms": p50_total,
                "p95_ms": p95_total,
            }
        },
        "suppression": suppression_stats,
        "active_connections": len(ws_delivery_manager.active_connections)
    }


@q4_router.post("/config/thresholds")
async def update_thresholds(req: ThresholdConfigRequest):
    """Configures suppression thresholds at runtime."""
    suppression_engine.min_confidence_threshold = req.min_confidence
    suppression_engine.cooldown_seconds = req.cooldown_seconds
    return {
        "status": "updated",
        "min_confidence": suppression_engine.min_confidence_threshold,
        "cooldown_seconds": suppression_engine.cooldown_seconds
    }


@q4_router.post("/config/priorities")
async def update_priorities(req: PriorityConfigRequest):
    """Configures priority rankings dynamically at runtime."""
    for k, v in req.mapping.items():
        priority_manager.set_priority(k, v)
    return {
        "status": "updated",
        "priorities": priority_manager.get_mapping()
    }


# ---------------------------------------------------------------------
# Serve Agent Dashboard HTML
# ---------------------------------------------------------------------
@q4_router.get("/dashboard", response_class=HTMLResponse)
async def serve_agent_dashboard():
    dashboard_file = Path(__file__).parent.parent.parent / "dashboard" / "index.html"
    if dashboard_file.exists():
        return HTMLResponse(content=dashboard_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard file not found.</h1>", status_code=404)
