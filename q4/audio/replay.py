import asyncio
import time
from typing import AsyncGenerator, List, Dict, Any, Optional
from q4.audio.streaming import AudioChunk


class RealtimeCallReplayer:
    """
    Replays multi-turn audio calls in strict real-time speed.
    Splits utterances into realistic streaming chunks (e.g. 200ms - 250ms)
    and yields them with precise chronological pacing.
    """

    def __init__(self, chunk_duration_ms: float = 250.0, time_scale: float = 1.0):
        """
        :param chunk_duration_ms: Length of each streaming audio slice in milliseconds.
        :param time_scale: 1.0 = strict real-time wall clock speed, 0.1 = 10x speedup for CI tests.
        """
        self.chunk_duration_ms = chunk_duration_ms
        self.time_scale = time_scale

    async def stream_call(
        self,
        call_id: str,
        turns: List[Dict[str, Any]]
    ) -> AsyncGenerator[AudioChunk, None]:
        """
        Asynchronously streams audio chunks turn-by-turn in real time.
        Each turn dict format:
        {
            "speaker": "customer" | "agent",
            "text": "spoken utterance string",
            "pause_after_ms": 500  # natural conversational pause before next speaker
        }
        """
        seq = 0
        words_per_sec = 2.8  # ~168 WPM standard conversational pace
        words_per_chunk = max(1, int(words_per_sec * (self.chunk_duration_ms / 1000.0)))

        for turn_idx, turn in enumerate(turns):
            speaker = turn["speaker"].lower()
            text = turn["text"].strip()
            channel = 0 if speaker == "agent" else 1
            words = text.split()

            # Stream words across chunks
            word_idx = 0
            while word_idx < len(words):
                chunk_words = words[word_idx: word_idx + words_per_chunk]
                word_idx += len(chunk_words)
                is_boundary = (word_idx >= len(words))

                chunk = AudioChunk(
                    call_id=call_id,
                    chunk_id=f"{call_id}_chunk_{seq:05d}",
                    sequence=seq,
                    channel=channel,
                    speaker=speaker,
                    duration_ms=self.chunk_duration_ms,
                    received_at=time.perf_counter(),
                    is_speech=True,
                    is_turn_boundary=is_boundary,
                    text_segment=" ".join(chunk_words)
                )
                seq += 1

                yield chunk

                # Sleep to enforce real-time streaming cadence
                if self.time_scale > 0:
                    sleep_sec = (self.chunk_duration_ms / 1000.0) * self.time_scale
                    await asyncio.sleep(sleep_sec)

            # Natural inter-turn pause
            pause_ms = turn.get("pause_after_ms", 400.0)
            if pause_ms > 0 and self.time_scale > 0:
                await asyncio.sleep((pause_ms / 1000.0) * self.time_scale)


# =============================================================================
# PRE-BUILT EVALUATION SCENARIOS
# =============================================================================

SAMPLE_CALLS = {
    # 1. Missed Cross-Sell (Auto Insurance)
    "call_cross_sell": [
        {"speaker": "agent", "text": "Thank you for calling Darwix Insurance. I can see you are reviewing your Honda Civic policy today."},
        {"speaker": "customer", "text": "Yes, that's right. Actually, I have another vehicle too."},
        {"speaker": "agent", "text": "Let me look at your current deductible for the Civic."},
        {"speaker": "customer", "text": "Can I add it to the policy as well?"},
        {"speaker": "agent", "text": "Sure, let's look into multi-vehicle coverage options."}
    ],

    # 2. Compliance Gap (Mandatory Disclosure Omitted)
    "call_compliance_gap": [
        {"speaker": "customer", "text": "I would like to finalize my auto insurance policy binding now."},
        {"speaker": "agent", "text": "Great, I have all your vehicle details and credit card ready to process."},
        {"speaker": "customer", "text": "Okay, let's continue and charge the first month deposit."},
        {"speaker": "agent", "text": "Okay, your card has been charged and the policy is active."}
    ],

    # 3. Rising Frustration
    "call_rising_frustration": [
        {"speaker": "agent", "text": "Could you please confirm your date of birth and policy number?"},
        {"speaker": "customer", "text": "I've already explained this twice to your colleague."},
        {"speaker": "agent", "text": "I apologize, my system reloaded so I need it again."},
        {"speaker": "customer", "text": "I already told you this three times! I don't understand why you're asking again!"}
    ],

    # 4. Payment Difficulty
    "call_payment_difficulty": [
        {"speaker": "agent", "text": "Your monthly premium installment of three hundred dollars is due this Friday."},
        {"speaker": "customer", "text": "I don't think I can make the payment this month due to unexpected medical bills."}
    ],

    # 5. Noisy / Ambiguous (Low confidence -> suppress nudge)
    "call_noisy_ambiguous": [
        {"speaker": "agent", "text": "Hello, how can I help you today?"},
        {"speaker": "customer", "text": "I... uh... maybe... another... mumble..."}
    ],

    # 6. False Positive Cross-Sell Contrast (Third-party mention)
    "call_false_positive_cross_sell": [
        {"speaker": "agent", "text": "Are you the only driver registered on this vehicle?"},
        {"speaker": "customer", "text": "Yes, my brother has another vehicle in Seattle, but I only drive this one."}
    ]
}
