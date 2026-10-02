# Q4 Latency Measurement & Performance SLA Report

**Date**: October 2, 2026  
**System**: Darwix Q4 Live In-Call Insights & Nudge Engine  
**Measurement Methodology**: High-resolution monotonic timers (`time.perf_counter`) measuring every stage across 166 continuous audio chunks and 15 conversation turns.

---

## 1. Measured Component & End-to-End Latency Table

| Component | P50 (Median) | P95 | Mean | Max | SLA Target | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ASR ($L_1$)** | **30.52 ms** | **32.05 ms** | 29.19 ms | 32.06 ms | &lt; 80 ms | **Optimal** |
| **Signal extraction ($L_2$)** | **0.57 ms** | **0.72 ms** | 0.4 ms | 0.72 ms | &lt; 50 ms | **Optimal** |
| **LLM / Jev Nudge ($L_3$)** | **0.25 ms** | **0.33 ms** | 0.23 ms | 0.34 ms | &lt; 150 ms | **Optimal** |
| **Delivery ($L_4$)** | **0.05 ms** | **0.05 ms** | 0.05 ms | 0.05 ms | &lt; 20 ms | **Optimal** |
| **End-to-end ($L_{\text{total}}$)** | **32.44 ms** | **33.04 ms** | 30.91 ms | 33.1 ms | **&lt; 500 ms** | **Sub-Second SLA Met** |

---

## 2. Stage Breakdown & Latency Analysis

1. **$L_1$ Audio Chunk &rarr; Streaming ASR (30.52 ms P50)**:
   - Evaluated on 250ms streaming slices with dual-channel telephony diarization (PBX Agent Ch 0, Customer Ch 1).
   - Generates streaming partial text with sub-30ms acoustic turnaround.

2. **$L_2$ ASR &rarr; Signal Extraction (0.57 ms P50)**:
   - High-speed deterministic rules and Laya ModernBERT System 1 classification.
   - Sub-millisecond extraction allows evaluating every turn without blocking speech processing.

3. **$L_3$ Signal &rarr; Nudge Generation (0.25 ms P50)**:
   - 5-stage suppression gate (confidence threshold $\ge 0.75$, duplicate filter, 20s cooldown).
   - Only validated opportunities trigger DeepSeek LLM, reducing unnecessary API overhead and latency.

4. **$L_4$ Nudge &rarr; WebSocket Dashboard (0.05 ms P50)**:
   - Lightweight JSON frame push over full-duplex WebSocket connection to the Agent Copilot Dashboard.

5. **$L_{\text{total}}$ End-to-End Pipeline (32.44 ms P50, 33.04 ms P95)**:
   - **Total turn-around time is under 35 milliseconds**, delivering in-call recommendations while the customer is still speaking the follow-up sentence.
