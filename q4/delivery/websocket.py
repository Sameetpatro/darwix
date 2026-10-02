import json
import time
from typing import Set, Dict, Any, List
from fastapi import WebSocket
from app.logging_config import logger
from q4.nudge.models import NudgeEvent


class WebSocketDeliveryManager:
    """
    Manages real-time WebSocket connections with agent copilot dashboards.
    Broadcasts live transcripts, detected signals, suppression events, and nudges.
    Measures Latency L4 (Nudge -> Dashboard).
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.delivery_latencies_l4: List[float] = []

    async def connect(self, websocket: WebSocket):
        """Accepts and registers a new dashboard connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("[WS_DELIVERY] Agent dashboard connected. Active sessions: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        """Removes a disconnected dashboard."""
        self.active_connections.discard(websocket)
        logger.info("[WS_DELIVERY] Agent dashboard disconnected. Active sessions: %d", len(self.active_connections))

    async def broadcast_nudge(self, nudge: NudgeEvent) -> float:
        """
        Broadcasts a generated nudge event to all connected agent dashboards.
        Measures L4 delivery latency.
        """
        t0 = time.perf_counter()
        payload = nudge.model_dump()
        payload["delivered_at"] = time.time()

        if self.active_connections:
            message_str = json.dumps(payload)
            disconnected = set()
            for ws in self.active_connections:
                try:
                    await ws.send_text(message_str)
                except Exception as exc:
                    logger.warning("[WS_DELIVERY] Failed to send to dashboard: %s", exc)
                    disconnected.add(ws)

            for ws in disconnected:
                self.active_connections.discard(ws)

        delivery_ms = round((time.perf_counter() - t0) * 1000, 2)
        # Ensure positive non-zero measurement for ultra-fast local loop
        delivery_ms = max(delivery_ms, 0.05)
        self.delivery_latencies_l4.append(delivery_ms)

        logger.info(
            "[WS_DELIVERY] Delivered Nudge '%s' (%s) to %d dashboard(s) in %.2f ms",
            nudge.headline, nudge.priority, len(self.active_connections), delivery_ms
        )
        return delivery_ms

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """Broadcasts general conversation telemetry (transcripts, signals, metrics)."""
        if not self.active_connections:
            return

        payload = {
            "event": event_type,
            "timestamp": time.time(),
            "data": data
        }
        message_str = json.dumps(payload)
        disconnected = set()
        for ws in self.active_connections:
            try:
                await ws.send_text(message_str)
            except Exception:
                disconnected.add(ws)

        for ws in disconnected:
            self.active_connections.discard(ws)

    def get_latency_stats(self) -> Dict[str, float]:
        """Calculates percentile distribution for L4 delivery latency."""
        if not self.delivery_latencies_l4:
            return {"mean_ms": 0.0, "p50_ms": 0.0, "p90_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "count": 0}

        sorted_lat = sorted(self.delivery_latencies_l4)
        n = len(sorted_lat)
        return {
            "mean_ms": round(sum(sorted_lat) / n, 2),
            "p50_ms": round(sorted_lat[int(n * 0.50)], 2),
            "p90_ms": round(sorted_lat[min(int(n * 0.90), n - 1)], 2),
            "p95_ms": round(sorted_lat[min(int(n * 0.95), n - 1)], 2),
            "max_ms": round(sorted_lat[-1], 2),
            "count": n
        }


ws_delivery_manager = WebSocketDeliveryManager()
