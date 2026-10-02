from enum import Enum
from typing import Dict, Any


class NudgePriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PriorityManager:
    """
    Configurable priority manager for live agent nudges.
    Priorities are NOT hardcoded blindly; they are configurable at runtime.
    Default hierarchy:
      - compliance_gap -> high
      - payment_difficulty -> high / medium
      - frustration -> high
      - cross_sell_opportunity -> medium
      - info / general -> low
    """

    DEFAULT_MAPPING = {
        "compliance_gap": NudgePriority.HIGH.value,
        "payment_difficulty": NudgePriority.HIGH.value,
        "frustration": NudgePriority.HIGH.value,
        "cross_sell_opportunity": NudgePriority.MEDIUM.value,
        "info": NudgePriority.LOW.value,
    }

    PRIORITY_WEIGHTS = {
        NudgePriority.CRITICAL.value: 100,
        NudgePriority.HIGH.value: 80,
        NudgePriority.MEDIUM.value: 50,
        NudgePriority.LOW.value: 20,
    }

    def __init__(self, custom_mapping: Dict[str, str] = None):
        self._mapping = dict(self.DEFAULT_MAPPING)
        if custom_mapping:
            self._mapping.update(custom_mapping)

    def get_priority(self, signal_type: str, severity: str = "medium") -> str:
        """Determines nudge priority based on signal type and severity."""
        if severity == "critical":
            return NudgePriority.CRITICAL.value
        return self._mapping.get(signal_type, NudgePriority.MEDIUM.value)

    def set_priority(self, signal_type: str, priority: str):
        """Allows dynamic runtime configuration of signal priorities."""
        if priority in [p.value for p in NudgePriority]:
            self._mapping[signal_type] = priority

    def get_mapping(self) -> Dict[str, str]:
        return dict(self._mapping)


priority_manager = PriorityManager()
