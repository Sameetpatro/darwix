# Philippines Voice Bot Transcript

## Call Metadata
- **Case ID**: `ph_case_5_unsupported_fallback`
- **Scenario Title**: Case 5: Caller Asking Unsupported / Out-of-Scope Questions (Strict Fallback)
- **Description**: Caller asks out-of-scope non-financial questions (cookie baking, crypto trading); agent adheres to strict anti-hallucination fallback in polite Taglish.
- **Market**: Philippines (Life Insurance / Bancassurance)
- **Primary TTS Voice**: `fil-PH-BlessicaNeural`
- **Session ID**: `eval_ph_case_5_unsupported_fallback_1790921106`

---

## Conversation Transcript

### Turn 0 (Initial Bot Greeting)
**Vani**: "Magandang araw po! Welcome sa Darwix Life Bancassurance. Ako po si Vani, ang inyong insurance specialist. Nandito po ako para tulungan kayo sa life protection at bancassurance plans. Paano ko po kayo matutulungan today?"

- **Language**: `taglish`
### Turn 1
**Customer**: "Magandang araw! Pwede po bang magtanong?"

**Vani**: "Ilang taon na po kayo sa kasalukuyan upang matiyak ang tamang halaga ng premium?"

#### Turn Metadata
- **Detected Language / Dialect**: `fil`
- **Intent Detected**: `general`
- **Escalated to Human**: `False`
- **Qualification Completed**: `False`
- **Turn Latency**: `2246.1 ms` (TTS: `2245.2 ms`)
- **Current Profile Slots**: `{"applicant_name": null, "age": null, "monthly_budget": null, "target_coverage": null, "insurance_type": null, "beneficiary_relation": null, "health_declaration": null, "bank_partner": null}`
- **Missing Slots**: `["age", "target_coverage", "monthly_budget", "beneficiary_relation", "bank_partner"]`
- **Knowledge Retrieved**: `None (Deterministic Underwriting / Direct Intent Logic)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/philippines/eval_ph_case_5_unsupported_fallback_1790921106_turn_1790921106238.mp3`

### Turn 2
**Customer**: "Can you teach me how to bake homemade chocolate chip cookies with melted butter?"

**Vani**: "I don't have reliable information about that at the moment. I can connect you with a licensed Financial Advisor if you'd like."

#### Turn Metadata
- **Detected Language / Dialect**: `en`
- **Intent Detected**: `unsupported`
- **Escalated to Human**: `False`
- **Qualification Completed**: `False`
- **Turn Latency**: `4106.7 ms` (TTS: `4106.1 ms`)
- **Current Profile Slots**: `{"applicant_name": null, "age": null, "monthly_budget": null, "target_coverage": null, "insurance_type": null, "beneficiary_relation": null, "health_declaration": null, "bank_partner": null}`
- **Missing Slots**: `["age", "target_coverage", "monthly_budget", "beneficiary_relation", "bank_partner"]`
- **Knowledge Retrieved**: `None (Deterministic Underwriting / Direct Intent Logic)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/philippines/eval_ph_case_5_unsupported_fallback_1790921106_turn_1790921108484.mp3`

### Turn 3
**Customer**: "May cryptocurrency trading o bitcoin investments din ba kayo dito sa Darwix?"

**Vani**: "Wala po akong maaasahang impormasyon tungkol diyan sa ngayon. Pwede po kitang ikonekta sa isang licensed Financial Advisor kung gusto niyo po."

#### Turn Metadata
- **Detected Language / Dialect**: `taglish`
- **Intent Detected**: `unsupported`
- **Escalated to Human**: `False`
- **Qualification Completed**: `False`
- **Turn Latency**: `2428.7 ms` (TTS: `2427.2 ms`)
- **Current Profile Slots**: `{"applicant_name": null, "age": null, "monthly_budget": null, "target_coverage": null, "insurance_type": null, "beneficiary_relation": null, "health_declaration": null, "bank_partner": null}`
- **Missing Slots**: `["age", "target_coverage", "monthly_budget", "beneficiary_relation", "bank_partner"]`
- **Knowledge Retrieved**: `None (Deterministic Underwriting / Direct Intent Logic)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/philippines/eval_ph_case_5_unsupported_fallback_1790921106_turn_1790921112591.mp3`

### Final Underwriting Profile
```json
{
  "applicant_name": null,
  "age": null,
  "monthly_budget": null,
  "target_coverage": null,
  "insurance_type": null,
  "beneficiary_relation": null,
  "health_declaration": null,
  "bank_partner": null
}
```
