from typing import Dict, Any, List, Optional
import uuid

from q2.models.knowledge_record import KnowledgeRecord, ConflictRecord, NormalizedEntities
from app.logging_config import logger


class ConflictDetector:
    """
    Identifies policy contradictions and parameter discrepancies across knowledge records.
    Ensures that conflicting terms (e.g. 6 months vs 12 months minimum operating age,
    or differing credit scores) are explicitly captured as structured metadata.
    """

    def __init__(self):
        # Maps (product_name, field_name) -> List of (record_id, value, source, title)
        self._rule_registry: Dict[tuple, List[Dict[str, Any]]] = {}

    def detect_conflicts(
        self,
        record_id: str,
        title: str,
        product: Optional[str],
        entities: NormalizedEntities,
        source: str,
    ) -> List[ConflictRecord]:
        """
        Scans normalized entities against previously registered records to find contradictions.
        Returns a list of ConflictRecord instances.
        """
        conflicts: List[ConflictRecord] = []
        target_product = product or (entities.loan_products[0] if entities.loan_products else "General Eligibility")

        # Fields to audit for conflicts
        check_fields = [
            ("min_months_in_business", entities.time_in_business_months, "months in business"),
            ("min_credit_score", entities.min_credit_score, "credit score minimum"),
            ("min_revenue_monthly_usd", entities.min_revenue_monthly_usd, "minimum monthly revenue ($ USD)"),
            ("min_apr", entities.min_apr, "minimum APR (%)"),
            ("prepayment_penalty_allowed", entities.prepayment_penalty_allowed, "prepayment penalty policy"),
        ]

        for field_name, value, label in check_fields:
            if value is None:
                continue

            registry_key = (target_product.lower(), field_name)
            existing_assertions = self._rule_registry.get(registry_key, [])

            for existing in existing_assertions:
                existing_val = existing["value"]
                existing_id = existing["record_id"]
                existing_source = existing["source"]

                # Compare values
                is_conflicting = False
                severity = "medium"

                if field_name == "prepayment_penalty_allowed":
                    if value != existing_val:
                        is_conflicting = True
                        severity = "high"
                        desc = (
                            f"Contradictory Prepayment Penalty Policy for {target_product}: "
                            f"Current record states penalty={value} (source: {source}), "
                            f"whereas record '{existing_id}' states penalty={existing_val} (source: {existing_source})."
                        )
                elif isinstance(value, (int, float)) and isinstance(existing_val, (int, float)):
                    # Check relative discrepancy
                    if value != existing_val:
                        ratio = max(value, existing_val) / max(min(value, existing_val), 1)
                        if ratio > 1.25:  # Greater than 25% divergence
                            is_conflicting = True
                            severity = "high" if ratio >= 1.5 else "medium"
                            desc = (
                                f"Discrepancy in {label} for {target_product}: "
                                f"Current record specifies {value}, whereas record '{existing_id}' specifies {existing_val}."
                            )

                if is_conflicting:
                    conflict = ConflictRecord(
                        field=field_name,
                        product=target_product,
                        conflicting_record_id=existing_id,
                        this_value=value,
                        conflicting_value=existing_val,
                        description=desc,
                        severity=severity,
                    )
                    conflicts.append(conflict)
                    logger.warning("[CONFLICT-DETECTOR] %s", desc)

            # Register current assertion into rule registry
            if registry_key not in self._rule_registry:
                self._rule_registry[registry_key] = []
            self._rule_registry[registry_key].append({
                "record_id": record_id,
                "value": value,
                "source": source,
                "title": title,
            })

        return conflicts

    def reset(self):
        """Clears the rule registry."""
        self._rule_registry.clear()


conflict_detector = ConflictDetector()
