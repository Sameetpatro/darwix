# Darwix — AI Business Loan Voice Agent (Vani)

An autonomous AI voice agent designed for business loan qualification, conversational dialogue, objection handling, strict anti-hallucination knowledge base retrieval, and human escalation. Powered by **Vani**, the autonomous commercial lending specialist at **Darwix**.

Built phase-by-phase in strict accordance with [`IMPLEMENTATION.md`](./IMPLEMENTATION.md).

---

## 1. System Architecture

```text
                                Customer Voice
                                      │
                                      ▼
                               Voice Softphone
                              (Web Audio / Mic)
                                      │
                                      ▼
                             Speech-to-Text (ASR)
                             (Web Speech Engine)
                                      │
                                      ▼
                           Conversation State & HUD
                                      │
                                      ▼
                        Qualification & Dialog Manager
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
                 ▼                                         ▼
         Decision Logic                           Darwix Knowledge Base
     (9 Slots, Rules, Conflicts)                    (Hybrid RAG Engine)
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                                  LLM Engine
                           (DeepSeek V3 / Fallback)
                                      │
                                      ▼
                            Text-to-Speech (TTS)
                         (Microsoft Neural Voice)
                                      │
                                      ▼
                                Customer Audio
                             (Real-time Playback)
```

### Human Escalation Flow
```text
Customer Utterance
       │
       ▼
AI Voice Agent (Vani)
       │
       ├── Explicit Human Request ("speak to human", "manager", "representative")
       └── Unresolved Complex Underwriting Exception
       │
       ▼
Human Senior Lending Officer (Warm Transfer)
```

---

## 2. Implementation Overview by Phase

### Part 1 — Basic Voice Pipeline
- Interactive browser calling softphone interface (`http://localhost:8000`).
- Continuous Web Speech ASR integration, DeepSeek LLM engine, and Microsoft Edge Neural TTS (`en-US-EmmaMultilingualNeural`).
- Canvas audio waveform visualizer and real-time call stopwatch.
- Per-turn latency tracking (ASR latency, LLM latency, TTS latency, and total roundtrip latency).
- Dual-format transcript persistence (machine-readable JSON + formatted text TXT).

### Part 2 — Loan Qualification Engine
- 9-Slot Qualification Schema:
  1. `customer_name`: Full borrower name.
  2. `business_name`: Registered legal business name.
  3. `business_type`: Entity structure (LLC, C-Corp, S-Corp, Sole Proprietor, Partnership).
  4. `business_age`: Operating history (months or years).
  5. `monthly_revenue`: Gross monthly business revenue.
  6. `requested_amount`: Desired loan funding amount.
  7. `loan_purpose`: Use of funds (working capital, equipment, expansion, inventory, payroll).
  8. `existing_loans`: Current business debt or merchant cash advances.
  9. `location`: City and State.
- Multi-slot extraction: extracts multiple volunteered slots at once, asking only for missing fields.
- Information conflict detection (revenue-to-loan leverage ratio > 4x, conflicting business operating history).
- Explicit verbal confirmation before underwriting evaluation.
- Underwriting decision engine (`PRE_QUALIFIED`, `NEEDS_REVIEW`, `DISQUALIFIED`, `ESCALATED`).
- Human escalation triggers for representative/agent requests.
- Live qualification checklist card with real-time green checkmarks.

### Part 3 — Knowledge Base Integration & Anti-Hallucination RAG
- 5 comprehensive markdown knowledge base documents in [`data/knowledge_base/`](./data/knowledge_base/) (21 searchable chunks):
  - `loan_products.md`: Commercial Term Loans, Lines of Credit, Equipment Financing, SBA 7(a), Working Capital.
  - `eligibility_and_policies.md`: Underwriting rules, minimum revenue ($10k/mo), time in business (6+ mos), 50 US states, restricted industries (gambling, adult, crypto, cannabis).
  - `faqs.md`: Funding timeline (24-48h), soft credit pull (zero score impact), $0 upfront fees guarantee, required documentation (bank statements), zero prepayment penalties.
  - `rates_and_terms.md`: Interest rate tier matrix (Prime 5.99%–10.99%, Standard 11.00%–17.99%, Alternative 18.00%–24.99%).
  - `objections_guide.md`: Objections handling for rates, fees, and paperless uploads.
- Hybrid TF-IDF keyword & stemming search engine with FAQ question prioritization.
- Informative token filtering to eliminate false-positive matches on ungrounded queries.
- Strict anti-hallucination fallback:
  > *"I don't have reliable information about that at the moment. I can connect you with a human representative if you'd like."*
- Source citations emitted for every retrieved turn (`Darwix KB: <file> (<chunk_id>)`).
- Speech bubble citation badges rendered dynamically in the softphone interface.

### Part 4 — Testing, Benchmarking & Submission Evidence
- Complete automated pytest suite with **32 tests** covering KB, LLM, Pipeline, Qualification, Server, State, TTS, and Scenarios.
- Dedicated benchmark runner (`scripts/run_benchmarks.py`) executing 3 full multi-turn calls with audio synthesis and latency measurements.
- Call transcripts and recordings stored in [`recordings/`](./recordings/) and [`transcripts/`](./transcripts/).

---

## 3. Core Evaluation Scenarios

The test suite formally validates the 6 mandatory evaluation scenarios:

| Scenario | Test Function | Description | Outcome |
| :--- | :--- | :--- | :--- |
| **1. Cooperative Customer** | `test_scenario_1_cooperative_customer` | Applicant provides all 9 slots cleanly, confirms details. | `PRE_QUALIFIED` |
| **2. Objection Handling** | `test_scenario_2_objection_handling` | Applicant concerns regarding high rates & fees handled with KB reassurance. | Resumed qualification |
| **3. Incomplete Information** | `test_scenario_3_incomplete_information` | Vague or minimal answers; agent methodically prompts only for missing fields. | Progressive slot gathering |
| **4. Conflicting Information** | `test_scenario_4_conflicting_information` | Excessive loan amount ($2M requested on $8k/mo revenue = 250x leverage ratio). | Discrepancy flagged & clarified |
| **5. Out-of-Scope Question** | `test_scenario_5_out_of_scope_question` | Inquiries regarding cryptocurrency trading / Bitcoin speculation. | Strict non-hallucination fallback |
| **6. Human Assistance** | `test_scenario_6_human_assistance_request` | Caller explicitly asks to speak with a human agent or manager. | `ESCALATED` to lending officer |

---

## 4. Benchmark Calls & Evidence

Execution of `scripts/run_benchmarks.py` generated 3 verified end-to-end calls:

### Call 1: Cooperative Customer Pre-Qualification
- **Call ID**: `call_1_cooperative_prequal`
- **Caller**: Michael Chang (Austin, TX — Horizon Tech Services LLC)
- **Requested**: $150,000 for equipment upgrades ($65,000/mo revenue, 3 years in business, no debt)
- **Turns**: 11 total (5 caller, 6 agent)
- **Outcome**: `PRE_QUALIFIED` for Prime Commercial Term Loan
- **Transcripts**: [`call_1_cooperative_prequal.json`](./transcripts/call_1_cooperative_prequal.json) & [`call_1_cooperative_prequal_transcript.txt`](./transcripts/call_1_cooperative_prequal_transcript.txt)
- **Audio Recordings**: [`recordings/call_1_cooperative_prequal_turn_*.mp3`](./recordings/)

### Call 2: Objection Handling & Knowledge Base Inquiries
- **Call ID**: `call_2_objections_and_faqs`
- **Caller**: Elena Rostova (Seattle, WA — BlueWave Logistics Corp)
- **Questions Asked**: Prepayment penalties & funding speed timeline
- **Citations Provided**:
  - `Darwix KB: faqs.md (faq-prepayment-penalty)`
  - `Darwix KB: faqs.md (faq-funding-speed)`
- **Turns**: 11 total (5 caller, 6 agent)
- **Outcome**: `PRE_QUALIFIED` for Prime Commercial Term Loan
- **Transcripts**: [`call_2_objections_and_faqs.json`](./transcripts/call_2_objections_and_faqs.json) & [`call_2_objections_and_faqs_transcript.txt`](./transcripts/call_2_objections_and_faqs_transcript.txt)
- **Audio Recordings**: [`recordings/call_2_objections_and_faqs_turn_*.mp3`](./recordings/)

### Call 3: Out-of-Scope Fallback & Unrealistic Loan Leverage
- **Call ID**: `call_3_fallback_and_high_leverage`
- **Caller**: Daniel Price (Chicago, IL — Swift Retail LLC)
- **Questions Asked**: Using loan for cryptocurrency trading and Bitcoin mining
- **Fallback Triggered**: *"I don't have reliable information about that at the moment. I can connect you with a human representative if you'd like."*
- **Discrepancy Flagged**: Requested $1,500,000 on $12,000/mo revenue (125x monthly revenue, exceeding 4x limit)
- **Turns**: 11 total (5 caller, 6 agent)
- **Outcome**: Flagged for discrepancy and custom underwriter structuring
- **Transcripts**: [`call_3_fallback_and_high_leverage.json`](./transcripts/call_3_fallback_and_high_leverage.json) & [`call_3_fallback_and_high_leverage_transcript.txt`](./transcripts/call_3_fallback_and_high_leverage_transcript.txt)
- **Audio Recordings**: [`recordings/call_3_fallback_and_high_leverage_turn_*.mp3`](./recordings/)

---

## 5. Latency Measurements

Across benchmark calls, the latency breakdown is measured per turn:

| Pipeline Stage | Provider / Component | Median Latency | P95 Latency | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **ASR** | Web Speech API | ~110 ms | ~150 ms | Zero-latency client streaming |
| **Logic & RAG** | Hybrid TF-IDF / Decision Engine | ~3–8 ms | ~25 ms | Sub-10ms in-memory index search |
| **LLM (DeepSeek)** | DeepSeek V3 Chat API | ~800–1,200 ms | ~2,200 ms | Enabled when balance present |
| **TTS** | Edge Neural TTS | ~1,200–2,800 ms | ~4,900 ms | Full sentence audio synthesis |
| **Roundtrip** | End-to-End Voice Turn | ~1,800–2,900 ms | ~5,200 ms | Customer speech end to audio playback |

---

## 6. Directory Structure

```text
darwix/
├── .env                       # Local secrets & API keys (git-ignored)
├── .env.example               # Template configuration
├── .gitignore                 # Security exclusions (.env, recordings, logs, venv)
├── IMPLEMENTATION.md          # Multi-phase master specification
├── README.md                  # Comprehensive project documentation
├── pyproject.toml             # Build configuration
├── requirements.txt           # Python dependencies
├── start.py                   # FastAPI server entrypoint
├── recordings/                # Generated call audio mp3s
├── transcripts/               # Saved call transcripts (JSON and TXT)
├── logs/                      # Runtime application logs
├── data/
│   ├── benchmarks_summary.json # Compiled benchmark report
│   └── knowledge_base/        # Enterprise knowledge documents
│       ├── eligibility_and_policies.md
│       ├── faqs.md
│       ├── loan_products.md
│       ├── objections_guide.md
│       └── rates_and_terms.md
├── app/
│   ├── config.py              # Environment configuration loader
│   ├── logging_config.py      # Console and rotating file logging setup
│   ├── state.py               # CallSession, CallTurn, and SessionManager
│   ├── pipeline.py            # End-to-end voice pipeline coordinator
│   ├── server.py              # FastAPI server (REST & WebSocket endpoints)
│   ├── asr/
│   │   └── asr_handler.py     # Speech-to-text processing handler
│   ├── kb/
│   │   ├── loader.py          # Markdown document chunker & keyword extractor
│   │   ├── models.py          # KBChunk, SearchResult, RetrievalResponse
│   │   └── retriever.py       # Hybrid TF-IDF RAG & anti-hallucination engine
│   ├── llm/
│   │   ├── deepseek.py        # DeepSeek API client with error handling
│   │   └── mock_fallback.py   # Resilient fallback conversational dialog engine
│   ├── qualification/
│   │   ├── dialog_manager.py  # Turn-by-turn dialogue coordinator
│   │   ├── extractor.py       # Regex & pattern multi-slot entity extractor
│   │   ├── models.py          # LoanApplication, ValidationIssue, UnderwritingDecision
│   │   ├── objections.py      # Objection detection & human escalation triggers
│   │   └── rules.py           # Underwriting rules & conflict detection
│   ├── tts/
│   │   └── edge_tts_engine.py # Neural Edge-TTS engine & audio generator
│   └── static/
│       ├── index.html         # Softphone calling web interface
│       ├── css/style.css      # Dark glassmorphism styling
│       └── js/app.js          # Speech recognition, audio visualizer, latency HUD
├── scripts/
│   └── run_benchmarks.py      # Automated benchmark suite runner
└── tests/
    ├── test_kb.py             # Knowledge Base loader & RAG tests
    ├── test_llm.py            # Text cleaning & LLM error resilience tests
    ├── test_pipeline.py       # Full voice pipeline integration tests
    ├── test_qualification.py  # 9-slot qualification & rules tests
    ├── test_scenarios.py      # 6 mandatory Part 4 evaluation scenarios
    ├── test_server.py         # FastAPI HTTP endpoints tests
    ├── test_state.py          # Session & turn lifecycle unit tests
    └── test_tts.py            # Audio synthesis & file generation tests
```

---

## 7. Quick Start & Setup Instructions

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Modern web browser (Chrome, Edge, Safari, Firefox) with microphone permissions enabled.

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-username/darwix.git
cd darwix

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
cp .env.example .env
# Edit .env with your DEEPSEEK_API_KEY if desired
```

### 4. Run Automated Test Suite
```bash
PYTHONPATH=. .venv/bin/pytest tests/ -v
```
*(All 32 tests will execute and pass)*

### 5. Run Benchmarks
```bash
PYTHONPATH=. .venv/bin/python scripts/run_benchmarks.py
```
*(Simulates 3 complete calls, generates recordings in `recordings/`, transcripts in `transcripts/`, and summary in `data/benchmarks_summary.json`)*

### 6. Start the Web Softphone
```bash
.venv/bin/python start.py
```
Open your browser to [**http://localhost:8000**](http://localhost:8000):
1. Click **Start Voice Call**.
2. Hear Vani greet you.
3. Speak into your microphone or type in the input bar.
4. Watch the 9-slot checklist update with green checkmarks in real time.
5. Ask any loan policy question (e.g. *"Are there prepayment penalties?"*) and observe the source citation badge.
6. Click **End Call** to finalize and review the stored transcript.

---

## 8. Known Limitations & Production Improvement Plan

### Known Limitations
1. **TTS Roundtrip Overhead**: Edge-TTS generates high-fidelity neural MP3 audio over WAN, which accounts for ~1.5s–3.0s of the total turn latency.
2. **DeepSeek API Balance**: When DeepSeek credits are exhausted (returns 400 Insufficient Balance), the system relies on its built-in rule and dialog engine fallback to maintain conversational flow.
3. **Telephony Bridge**: Currently operates via an in-browser Web Audio softphone. Integrating with real PSTN phone numbers requires connecting to Twilio Voice or LiveKit SIP trunks.

### Production Improvement Plan
1. **Low-Latency Streaming TTS**: Integrate WebSocket streaming TTS (e.g. ElevenLabs WebSocket or Cartesia Sonic) to stream audio chunks under 250ms time-to-first-byte (TTFB).
2. **Telephony Integration**: Implement Twilio Voice Media Streams (`/ws/twilio`) or LiveKit WebRTC for inbound 1-800 phone numbers.
3. **CRM / Loan Origination System (LOS) Webhooks**: Automatically push pre-qualified applications to Salesforce, HubSpot, or commercial lending platforms (e.g. Blend, Ocrolus).
4. **Vector Embeddings**: Augment the keyword TF-IDF RAG with dense vector embeddings (e.g. BAAI/bge-small or OpenAI text-embedding-3-small) in an embedded LanceDB database for semantic matching.
