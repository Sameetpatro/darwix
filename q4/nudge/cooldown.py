import time
from typing import Dict, Tuple, Optional


class CooldownManager:
    """
    Manages cooldown periods to prevent spamming the human agent with repeated nudges.
    Specification:
      Same signal -> Nudge shown -> Cooldown = 20 seconds -> Suppress repeated signals.
    """

    def __init__(self, default_cooldown_seconds: float = 20.0):
        self.default_cooldown_seconds = default_cooldown_seconds
        # Key: (call_id, signal_type, topic) -> last_triggered_timestamp
        self._history: Dict[Tuple[str, str, str], float] = {}

    def is_on_cooldown(
        self,
        call_id: str,
        signal_type: str,
        topic: str = "general",
        cooldown_seconds: Optional[float] = None,
        current_time: Optional[float] = None
    ) -> Tuple[bool, float]:
        """
        Checks whether the specified signal is currently cooling down.
        Returns: (is_cooling_down: bool, remaining_seconds: float)
        """
        now = current_time or time.time()
        cd = cooldown_seconds if cooldown_seconds is not None else self.default_cooldown_seconds
        key = (call_id, signal_type, topic)

        last_time = self._history.get(key)
        if last_time is None:
            return False, 0.0

        elapsed = now - last_time
        if elapsed < cd:
            remaining = round(cd - elapsed, 1)
            return True, remaining

        return False, 0.0

    def record_nudge(
        self,
        call_id: str,
        signal_type: str,
        topic: str = "general",
        current_time: Optional[float] = None
    ):
        """Records that a nudge was successfully shown for cooldown tracking."""
        now = current_time or time.time()
        key = (call_id, signal_type, topic)
        self._history[key] = now

    def reset_call(self, call_id: str):
        """Clears cooldown records for a completed call."""
        keys_to_remove = [k for k in self._history if k[0] == call_id]
        for k in keys_to_remove:
            del self._history[k]


cooldown_manager = CooldownManager()
