# Q1 — Business-Loan Qualification Voice Agent

## What are we building?

We are building an AI voice agent that talks to a customer who is interested in a business loan.

The agent should:

- Talk naturally with the customer.
- Ask the required qualification questions.
- Collect important business information.
- Check basic qualification rules.
- Answer business-loan questions using the Question 2 knowledge base.
- Handle objections.
- Handle missing or conflicting information.
- Clearly say when information is unavailable.
- Escalate to a human when required.
- Record calls and produce transcripts for testing.

The final flow is:

Customer → Voice/ASR → Decision/Conversation Logic → Q2 Knowledge Base → LLM → TTS → Customer

---

# Part 1 — Basic Voice Pipeline

First, make a basic voice conversation work.

We need:

- Voice platform
- ASR
- LLM
- TTS
- Basic conversation state
- Environment variables
- Logging
- Error handling

At the end of Part 1, I should be able to call the agent and have a basic conversation.

Do not build the RAG system in this part.

---

# Part 2 — Loan Qualification

Now turn the basic voice bot into a real business-loan qualification agent.

The agent should collect:

- Customer name
- Business name
- Business type
- Business age
- Monthly revenue
- Requested loan amount
- Loan purpose
- Existing loans
- Location

The agent should:

- Ask only for missing information.
- Confirm important information.
- Detect conflicting information.
- Apply basic business rules.
- Handle objections.
- Escalate to a human when needed.

---

# Part 3 — Knowledge Base Integration

Connect the voice agent to the Question 2 knowledge base.

The agent should use the KB for:

- FAQs
- Product information
- Loan policies
- Qualification information
- Objections
- Business rules where appropriate

The agent must not invent answers.

If the KB does not contain the required information:

"I don't have reliable information about that at the moment. I can connect you with a human representative if you'd like."

Every retrieved answer should have a source that can be traced back to the knowledge base.

---

# Part 4 — Testing and Submission Evidence

Test at least:

1. Cooperative customer
2. Objection
3. Incomplete information
4. Conflicting information
5. Out-of-scope question
6. Human-assistance request

Record at least three calls.

For each call keep:

- Audio recording
- Transcript
- Scenario
- Expected behavior
- Actual behavior
- Result
- Problems observed

Measure latency where possible.

Prepare:

- README
- Architecture diagram
- Setup instructions
- `.env.example`
- Test results
- Call recordings
- Transcripts
- Known limitations
- Production improvement plan
- Video walkthrough

---

# API Keys / Credentials I Need

The exact providers will be selected during implementation, but expect to need credentials for:

## 1. Voice / Telephony Provider

Used to receive or make phone calls.

Need:

- API key
- Account/project ID if required
- Phone number
- Webhook configuration

## 2. Speech-to-Text Provider

Used to convert customer speech into text.

Need:

- API key
- Model name
- Language configuration

## 3. LLM Provider

Used for natural-language generation.

Need:

- API key
- Model name

## 4. Text-to-Speech Provider

Used to convert the AI response back into speech.

Need:

- API key
- Voice ID
- Language/voice configuration

## 5. Knowledge Base / Vector Database

This will be decided during Q2.

Possible requirements:

- Database URL
- API key
- Collection/index name

## 6. Optional Storage

Only needed if we decide to store recordings externally.

Possible requirements:

- Storage credentials
- Bucket name

---

# Important Security Rules

Never put API keys directly into source code.

Use:

`.env`

and commit only:

`.env.example`

Example:

```env
VOICE_API_KEY=
LLM_API_KEY=
TTS_API_KEY=
STT_API_KEY=
KB_API_KEY=
```

Never commit:

- API keys
- passwords
- private customer information
- real customer recordings
- real customer phone numbers

Use fictional/test customer information.

---

# Final Q1 Architecture

```text
                  Customer
                     │
                     ▼
              Voice / Telephony
                     │
                     ▼
                   ASR
                     │
                     ▼
             Conversation State
                     │
              ┌──────┴──────┐
              │             │
              ▼             ▼
          Decision       Q2 KB
           Logic       Retrieval
              │             │
              └──────┬──────┘
                     ▼
                    LLM
                     │
                     ▼
                    TTS
                     │
                     ▼
                  Customer
```

Human escalation:

```text
Customer
    │
    ▼
AI Voice Agent
    │
    │ escalation required
    ▼
Human Agent
```

The goal is not to build a huge system.

The goal is to build a small, reliable system that works, can be demonstrated, can be measured, and can be explained technically.
