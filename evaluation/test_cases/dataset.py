from typing import List, Dict, Any

EVALUATION_DATASET: List[Dict[str, Any]] = [
    # -------------------------------------------------------------
    # 1. TRUE POSITIVES: True In-Call Opportunities & Risks
    # -------------------------------------------------------------
    {
        "id": "cross_sell_true_01",
        "category": "cross_sell",
        "expected_signal": "cross_sell_opportunity",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "I actually have another car as well.",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Direct customer ownership of another vehicle"
    },
    {
        "id": "cross_sell_true_02",
        "category": "cross_sell",
        "expected_signal": "cross_sell_opportunity",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "Actually, I have another vehicle too. Can I add it to the policy?",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Explicit customer inquiry about adding second vehicle"
    },
    {
        "id": "cross_sell_true_03",
        "category": "cross_sell",
        "expected_signal": "cross_sell_opportunity",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "We own two cars, a Civic and a Ford F-150.",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Multi-car household ownership declaration"
    },
    {
        "id": "compliance_true_01",
        "category": "compliance",
        "expected_signal": "compliance_gap",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "Okay, let's continue and charge the first month deposit.",
        "stage": "binding_ready",
        "agent_disclosure_given": False,
        "description": "Customer advancing to binding without required disclosure"
    },
    {
        "id": "compliance_true_02",
        "category": "compliance",
        "expected_signal": "compliance_gap",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "Go ahead and bind the policy now, take my card details.",
        "stage": "binding_ready",
        "agent_disclosure_given": False,
        "description": "Binding request without mandatory regulatory disclosure"
    },
    {
        "id": "frustration_true_01",
        "category": "frustration",
        "expected_signal": "frustration",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "I already told you this three times! I don't understand why you're asking again!",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Repeated question complaint with explicit frustration"
    },
    {
        "id": "frustration_true_02",
        "category": "frustration",
        "expected_signal": "frustration",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "I've already explained this twice to your colleague, this is ridiculous.",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "High negative sentiment with repetition complaint"
    },
    {
        "id": "payment_true_01",
        "category": "payment_difficulty",
        "expected_signal": "payment_difficulty",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "I don't think I can make the payment this month due to unexpected medical bills.",
        "stage": "billing",
        "agent_disclosure_given": False,
        "description": "Explicit inability to make scheduled payment"
    },
    {
        "id": "payment_true_02",
        "category": "payment_difficulty",
        "expected_signal": "payment_difficulty",
        "expected_nudge": True,
        "speaker": "customer",
        "text": "I lost my job recently and I'm really struggling to pay this premium.",
        "stage": "billing",
        "agent_disclosure_given": False,
        "description": "Financial distress and hardship declaration"
    },

    # -------------------------------------------------------------
    # 2. FALSE POSITIVES / CONTRAST CASES (Must NOT generate nudge)
    # -------------------------------------------------------------
    {
        "id": "cross_sell_false_01",
        "category": "cross_sell",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "My brother has another vehicle in Seattle, but I only drive this Civic.",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "3rd-party vehicle ownership (brother) - Not customer cross-sell"
    },
    {
        "id": "cross_sell_false_02",
        "category": "cross_sell",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "My neighbor has a motorcycle that makes so much noise every morning.",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Neighbor asset mention - Not customer insurable interest"
    },
    {
        "id": "cross_sell_false_03",
        "category": "cross_sell",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "Someone else's vehicle hit my bumper in the parking lot yesterday.",
        "stage": "claims",
        "agent_disclosure_given": False,
        "description": "Accident third-party vehicle mention"
    },
    {
        "id": "compliance_false_01",
        "category": "compliance",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "Okay, let's continue and finalize the policy.",
        "stage": "binding_ready",
        "agent_disclosure_given": True,  # Already fulfilled!
        "description": "Customer advancing after agent already delivered required disclosure"
    },
    {
        "id": "frustration_false_01",
        "category": "frustration",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "I understand you need to verify my address twice for security, no problem at all.",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Cooperative customer mentioning 'twice' without frustration"
    },
    {
        "id": "payment_false_01",
        "category": "payment_difficulty",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "I will make the full payment online this Friday as scheduled.",
        "stage": "billing",
        "agent_disclosure_given": False,
        "description": "Normal timely payment confirmation"
    },

    # -------------------------------------------------------------
    # 3. AMBIGUOUS / NOISY SPEECH (Must NOT generate nudge)
    # -------------------------------------------------------------
    {
        "id": "ambiguous_noisy_01",
        "category": "noisy_speech",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "I... uh... maybe... another... mumble...",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Incomplete, fragmented, and hesitant speech"
    },
    {
        "id": "ambiguous_noisy_02",
        "category": "noisy_speech",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "Um... yeah... like... er...",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Filler words with no actionable semantic information"
    },
    {
        "id": "ambiguous_noisy_03",
        "category": "noisy_speech",
        "expected_signal": None,
        "expected_nudge": False,
        "speaker": "customer",
        "text": "Another... er... what was that again?",
        "stage": "discovery",
        "agent_disclosure_given": False,
        "description": "Question fragment with ambiguous 'another' keyword"
    }
]
