"""
Fallback Conversational Agent for Testing and Offline Scenarios.
Ensures the voice pipeline functions end-to-end even when external API quotas are exhausted.
"""
from typing import List, Dict
import re

SYSTEM_FALLBACK_PROMPT = """You are Vani, a professional and friendly business-loan specialist at Darwix.
Keep your spoken responses concise, friendly, and conversational (1 to 2 sentences max).
Ask clear questions one at a time."""


def generate_fallback_response(messages: List[Dict[str, str]]) -> str:
    """Intelligent rule-based fallback dialog generator for business loan inquiries."""
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    if not user_messages:
        return "Hello! Thank you for calling Darwix. I'm Vani. How can I assist you with your business loan needs today?"

    latest = user_messages[-1].lower()

    if any(w in latest for w in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return "Hello there! Glad you called. Are you looking to explore financing options for your business today?"

    if any(w in latest for w in ["yes", "yeah", "sure", "correct", "looking for a loan", "need money", "need funds"]):
        return "Wonderful! To get started and see what programs fit best, could you tell me your name and the name of your business?"

    if any(w in latest for w in ["my name is", "i am", "company", "business"]):
        return "Nice to meet you! What type of business do you operate, and how long has it been up and running?"

    if any(w in latest for w in ["year", "years", "month", "months", "llc", "corp", "retail", "tech", "construction", "restaurant"]):
        return "Got it, thank you. Approximately what is your average monthly revenue, and how much financing are you looking to secure?"

    if any(w in latest for w in ["revenue", "thousand", "million", "dollar", "$", "000", "borrow"]):
        return "Understood. And what is the primary purpose for the requested loan funds, like equipment, expansion, or working capital?"

    if any(w in latest for w in ["equipment", "expansion", "working capital", "inventory", "payroll"]):
        return "That sounds like a great use of capital. Do you currently have any existing commercial loans or debt balances?"

    if any(w in latest for w in ["no", "none", "don't have", "do not have", "have a loan", "already have"]):
        return "Thank you for sharing those details. Where is your business located, including city and state?"

    if any(w in latest for w in ["human", "representative", "agent", "real person", "escalate"]):
        return "I would be happy to connect you with a senior loan specialist. Let me transfer you right away."

    if any(w in latest for w in ["thank", "thanks", "bye", "goodbye"]):
        return "You're very welcome! Thank you for calling Darwix. Have a wonderful day!"

    # Default conversational reply
    return "Thank you for that information. Could you tell me a bit more about your business financing goals?"
