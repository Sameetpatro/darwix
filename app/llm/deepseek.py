import time
import re
from typing import List, Dict, Tuple, Optional
import httpx
from app.config import settings
from app.logging_config import logger
from app.llm.mock_fallback import generate_fallback_response

DEFAULT_SYSTEM_PROMPT = """You are Vani, an expert AI voice assistant at Darwix specializing in business loan qualification.
Your goal is to have a natural, helpful, and professional phone conversation with prospective business borrowers.

CRITICAL VOICE INSTRUCTIONS:
1. Speak in a concise, warm, natural tone suitable for a phone call.
2. Keep answers short: 1 to 2 sentences per turn. Never speak in long paragraphs or lists.
3. Do NOT use markdown, asterisks, bullet points, numbered lists, emojis, or symbols.
4. Ask only one clear question at a time to keep the conversation flowing smoothly.
5. If the caller asks to speak to a human or needs complex assistance, offer to escalate immediately.
"""


def clean_text_for_speech(text: str) -> str:
    """Removes markdown symbols, emojis, and unpronounceable characters for clean TTS audio."""
    # Remove markdown bold/italics
    cleaned = re.sub(r"[\*_#`~]", "", text)
    # Remove bullet points and list markers at line starts
    cleaned = re.sub(r"^\s*[-+*]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned, flags=re.MULTILINE)
    # Replace multiple spaces/newlines
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class DeepSeekClient:
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url.rstrip("/")
        self.model = settings.deepseek_model
        self.fallback_on_error = settings.llm_fallback_on_error
        self.last_error: Optional[str] = None
        self.consecutive_errors: int = 0

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 150,
        temperature: float = 0.6,
    ) -> Tuple[str, float, str]:
        """
        Sends conversation history to DeepSeek LLM.
        Returns: (response_text, latency_ms, provider_used)
        """
        start_time = time.perf_counter()

        formatted_messages = []
        has_system = False
        for m in messages:
            if m["role"] == "system":
                has_system = True
                formatted_messages.append({"role": "system", "content": m["content"]})
            else:
                formatted_messages.append(m)

        if not has_system:
            formatted_messages.insert(0, {"role": "system", "content": system_prompt or DEFAULT_SYSTEM_PROMPT})

        # Check API key configuration
        if not self.api_key or self.api_key.startswith("your_"):
            logger.warning("[LLM] DeepSeek API key not configured. Using fallback dialog agent.")
            reply = generate_fallback_response(formatted_messages)
            latency_ms = (time.perf_counter() - start_time) * 1000
            return clean_text_for_speech(reply), latency_ms, "fallback_agent"

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(endpoint, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    raw_content = data["choices"][0]["message"]["content"]
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    cleaned_content = clean_text_for_speech(raw_content)
                    self.consecutive_errors = 0
                    self.last_error = None
                    logger.info("[LLM] DeepSeek returned %d chars in %.1fms", len(cleaned_content), latency_ms)
                    return cleaned_content, latency_ms, "deepseek"

                # Handle API Error responses (e.g. 402 Insufficient Balance, 429 Rate Limit)
                error_body = response.text
                err_msg = f"HTTP {response.status_code}: {error_body}"
                self.last_error = err_msg
                self.consecutive_errors += 1

                if "Insufficient Balance" in error_body:
                    logger.warning("[LLM] DeepSeek Account Notice: Insufficient Balance. Gracefully switching to fallback engine.")
                else:
                    logger.error("[LLM] DeepSeek API error: %s", err_msg)

                if self.fallback_on_error:
                    reply = generate_fallback_response(formatted_messages)
                    latency_ms = (time.perf_counter() - start_time) * 1000
                    return clean_text_for_speech(reply), latency_ms, "deepseek_fallback_balance_exhausted"

                raise RuntimeError(f"DeepSeek LLM API error: {err_msg}")

        except Exception as exc:
            self.last_error = str(exc)
            self.consecutive_errors += 1
            logger.error("[LLM] Request exception: %s", exc)

            if self.fallback_on_error:
                reply = generate_fallback_response(formatted_messages)
                latency_ms = (time.perf_counter() - start_time) * 1000
                return clean_text_for_speech(reply), latency_ms, "deepseek_fallback_exception"

            raise


deepseek_client = DeepSeekClient()
