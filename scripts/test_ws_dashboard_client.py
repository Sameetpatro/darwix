import asyncio
import json
import websockets


async def test_live_websocket_client():
    uri = "ws://localhost:8000/q4/ws"
    print(f"Connecting to live Q4 WebSocket at {uri}...")

    async with websockets.connect(uri) as ws:
        # 1. Receive handshake
        greeting = await ws.recv()
        data = json.loads(greeting)
        print("Handshake received from server:", data.get("message"))
        assert data.get("event") == "connected"

        # 2. Trigger a simulation via REST while connected to WebSocket
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "http://localhost:8000/q4/simulate",
                json={"scenario": "call_cross_sell", "time_scale": 0.1}
            )
            print("Triggered simulation:", resp.json())

        # 3. Listen for streaming events over WebSocket
        events_received = []
        nudge_received = None

        while True:
            try:
                msg_str = await asyncio.wait_for(ws.recv(), timeout=5.0)
                msg = json.loads(msg_str)
                event_type = msg.get("event")
                events_received.append(event_type)

                if event_type == "audio_stream":
                    chunk_data = msg["data"]
                    # print dot for streaming chunk
                    print(".", end="", flush=True)

                elif event_type == "turn_finalized":
                    turn_data = msg["data"]
                    print(f"\n[TURN COMMITTED] [{turn_data['speaker'].upper()}]: \"{turn_data['text']}\"")

                elif event_type == "signal_detected":
                    sig = msg["data"]
                    print(f"[SIGNAL] {sig['type']} (Conf: {sig['confidence']:.2f})")

                elif event_type == "nudge":
                    nudge_received = msg
                    print("\n" + "=" * 60)
                    print(f"  >>> LIVE NUDGE DELIVERED TO DASHBOARD OVER WEBSOCKET <<<")
                    print(f"  Priority:   {msg['priority'].upper()}")
                    print(f"  Headline:   {msg['headline']}")
                    print(f"  Message:    {msg['message']}")
                    print(f"  Expires in: {msg['expires_in']}s")
                    print("=" * 60 + "\n")
                    # Acknowledge nudge back to server
                    await ws.send(json.dumps({"action": "acknowledge_nudge", "nudge_id": msg["nudge_id"]}))

                elif event_type == "latency_sample":
                    lat = msg["data"]
                    print(f"[LATENCY SAMPLE] L1={lat['L1_asr_ms']:.1f}ms | L2={lat['L2_signal_ms']:.2f}ms | L3={lat['L3_nudge_ms']:.2f}ms | L4={lat['L4_delivery_ms']:.2f}ms | L_total={lat['L_total_ms']:.2f}ms")

                elif event_type == "call_completed":
                    print("\n[CALL COMPLETED] Received call summary.")
                    break

            except asyncio.TimeoutError:
                print("\nTimeout waiting for events.")
                break

        print("\nTotal events received over WebSocket:", len(events_received))
        assert nudge_received is not None, "Failed to receive live nudge over WebSocket!"
        assert "audio_stream" in events_received
        assert "turn_finalized" in events_received
        assert "signal_detected" in events_received
        print("ALL REAL-TIME WEBSOCKET STREAMING CHECKS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(test_live_websocket_client())
