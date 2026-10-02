import time
from typing import Tuple, Dict, Any, Optional
from app.logging_config import logger
from app.llm.deepseek import deepseek_client
from q4.signals.models import ConversationSignal, SignalType
from q4.conversation.state import LiveCallState
from q4.nudge.models import NudgeEvent
from q4.nudge.priority import priority_manager


class NudgeGenerator:
    """
    Synthesizes concise, actionable in-call recommendations for the human agent.
    Uses DeepSeek LLM (replacing Gemini) selectively on high-confidence signals only.
    Measures Latency L3 (Signal -> Nudge Generation).
    """

    # Deterministic high-speed templates adhering to Q4 specification
    STANDARD_TEMPLATES = {
        SignalType.CROSS_SELL_OPPORTUNITY.value: {
            "headline": "CROSS-SELL",
            "context": "Customer mentioned another vehicle or insurable asset.",
            "message": "Ask if they'd like multi-vehicle coverage.",
            "expires_in": 25,
        },
        SignalType.COMPLIANCE_GAP.value: {
            "headline": "COMPLIANCE",
            "context": "Required disclosure has not been given.",
            "message": "Provide the required disclosure before continuing.",
            "expires_in": 15,
        },
        SignalType.FRUSTRATION.value: {
            "headline": "FRUSTRATION",
            "context": "Customer appears increasingly frustrated.",
            "message": "Acknowledge the concern before continuing.",
            "expires_in": 20,
        },
        SignalType.PAYMENT_DIFFICULTY.value: {
            "headline": "PAYMENT DIFFICULTY",
            "context": "Customer expressed difficulty making scheduled payments.",
            "message": "Offer payment relief options or installment grace period.",
            "expires_in": 25,
        },
    }

    def __init__(self):
        self.generation_latencies = []

    async def generate_nudge(
        self,
        signal: ConversationSignal,
        state: LiveCallState,
        use_deepseek: bool = True
    ) -> NudgeEvent:
        """
        Generates a concise NudgeEvent.
        Measures L3 latency.
        """
        t0 = time.perf_counter()

        # 1. Determine priority
        priority = priority_manager.get_priority(signal.type, signal.severity)

        # 2. Get baseline template
        template = self.STANDARD_TEMPLATES.get(
            signal.type,
            {
                "headline": signal.type.replace("_", " ").upper(),
                "context": f"Customer mentioned: {signal.evidence}",
                "message": "Address the customer's point before proceeding.",
                "expires_in": 20,
            }
        )

        headline = template["headline"]
        context = template["context"]
        message = template["message"]
        expires_in = template["expires_in"]

        # 3. For custom contextual phrasing, optionally query DeepSeek (bounded prompt for speed)
        if use_deepseek and deepseek_client.api_key and not deepseek_client.api_key.startswith("your_"):
            try:
                system_prompt = (
                    "You are the Darwix Real-Time Agent Copilot. Convert this conversation signal into an "
                    "extremely short (under 10 words) action directive starting with a verb for the human agent. "
                    "Output ONLY the single action directive, nothing else."
                )
                user_msg = (
                    f"Signal Type: {signal.type}\n"
                    f"Evidence: \"{signal.evidence}\"\n"
                    f"Default Action: {template['message']}"
                )
                llm_response, _, _ = await deepseek_client.generate_response(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg}
                    ],
                    max_tokens=25,
                    temperature=0.2
                )
                clean_directive = llm_response.strip().strip('"').strip("'")
                if 3 <= len(clean_directive.split()) <= 15:
                    message = clean_directive
            except Exception as exc:
                logger.warning("[NUDGE_GEN] DeepSeek generation fallback to template: %s", exc)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        self.generation_latencies.append(latency_ms)

        nudge = NudgeEvent(
            call_id=signal.call_id,
            priority=priority,
            type=signal.type,
            headline=headline,
            context=context,
            message=message,
            confidence=signal.confidence,
            expires_in=expires_in,
            timestamp=round(time.time(), 2),
            signal_id=signal.signal_id,
            generation_latency_ms=latency_ms
        )

        logger.info(
            "[NUDGE_ENGINE] Created Nudge (%s | %s | L3: %.2f ms): %s -> %s",
            nudge.priority.upper(), nudge.type, latency_ms, nudge.headline, nudge.message
        )
        return nudge


nudge_generator = NudgeGenerator()
