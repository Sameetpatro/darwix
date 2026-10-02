# Philippines Voice Bot Transcript

## Call Metadata
- **Case ID**: `ph_case_3_mixed_language`
- **Scenario Title**: Case 3: Mixed-Language Conversation (Taglish & English Code-Switching)
- **Description**: Caller fluidly mixes English technical financial terms with Tagalog grammar regarding riders, grace period, and policy lapses.
- **Market**: Philippines (Life Insurance / Bancassurance)
- **Primary TTS Voice**: `fil-PH-BlessicaNeural`
- **Session ID**: `eval_ph_case_3_mixed_language_1790921070`

---

## Conversation Transcript

### Turn 0 (Initial Bot Greeting)
**Vani**: "Magandang araw po! Welcome sa Darwix Life Bancassurance. Ako po si Vani, ang inyong insurance specialist. Nandito po ako para tulungan kayo sa life protection at bancassurance plans. Paano ko po kayo matutulungan today?"

- **Language**: `taglish`
### Turn 1
**Customer**: "Hello po, I would like to inquire about your term life insurance packages."

**Vani**: "Ilang taon na po kayo ngayon para ma-compute natin ang accurate rate?"

#### Turn Metadata
- **Detected Language / Dialect**: `taglish`
- **Intent Detected**: `qualification`
- **Escalated to Human**: `False`
- **Qualification Completed**: `False`
- **Turn Latency**: `1057.1 ms` (TTS: `1056.1 ms`)
- **Current Profile Slots**: `{"applicant_name": null, "age": null, "monthly_budget": null, "target_coverage": null, "insurance_type": "Darwix SecureTerm (Term Life)", "beneficiary_relation": null, "health_declaration": null, "bank_partner": null}`
- **Missing Slots**: `["age", "target_coverage", "monthly_budget", "beneficiary_relation", "bank_partner"]`
- **Knowledge Retrieved**: `None (Deterministic Underwriting / Direct Intent Logic)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/philippines/eval_ph_case_3_mixed_language_1790921070_turn_1790921070144.mp3`

### Turn 2
**Customer**: "Gusto ko pong malaman kung magkano yung premium for this policy if I add a critical illness rider?"

**Vani**: "Ayon po sa aming official guidelines:
5. Supplemental Riders (Add-On Benefits)
Policyholders can attach optional riders to enhance coverage:
1. Accidental Death and Dismemberment (ADB):"

#### Turn Metadata
- **Detected Language / Dialect**: `taglish`
- **Intent Detected**: `premium_information`
- **Escalated to Human**: `False`
- **Qualification Completed**: `False`
- **Turn Latency**: `3311.8 ms` (TTS: `3257.4 ms`)
- **Current Profile Slots**: `{"applicant_name": null, "age": null, "monthly_budget": null, "target_coverage": null, "insurance_type": "Darwix SecureTerm (Term Life)", "beneficiary_relation": null, "health_declaration": null, "bank_partner": null}`
- **Missing Slots**: `["age", "target_coverage", "monthly_budget", "beneficiary_relation", "bank_partner"]`
- **Knowledge Retrieved (1 chunks)**:
  - [None] Score: `0.016393` | Source: `None` | Content: *"..."*
- **Citation**: `Darwix PH KB: ph_life_insurance_handbook.md (Ph Life Insurance Handbook — 5. Supplemental Riders (Add-On Benefits))`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/philippines/eval_ph_case_3_mixed_language_1790921070_turn_1790921071255.mp3`

### Turn 3
**Customer**: "Kung mag-lapse ba yung policy ko, is there a 31-day grace period to settle the balance?"

**Vani**: "Ayon po sa Darwix policy guidelines, may 31-day grace period po tayo kapag may na-miss na due date, at nananatiling 100% active ang inyong coverage. Kung mag-lapse man po, pwede niyo pa po itong ma-reinstate within 3 years sa pamamagitan ng simpleng health declaration at pagbayad ng missed premiums.

By the way po, magkano po ang nais ninyong coverage o halaga ng proteksyon para sa inyong pamilya, halimbawa ₱1 million or ₱2 million?"

#### Turn Metadata
- **Detected Language / Dialect**: `taglish`
- **Intent Detected**: `lapse_inquiry`
- **Escalated to Human**: `False`
- **Qualification Completed**: `False`
- **Turn Latency**: `5385.1 ms` (TTS: `5363.2 ms`)
- **Current Profile Slots**: `{"applicant_name": null, "age": 31, "monthly_budget": null, "target_coverage": null, "insurance_type": "Darwix SecureTerm (Term Life)", "beneficiary_relation": null, "health_declaration": null, "bank_partner": null}`
- **Missing Slots**: `["target_coverage", "monthly_budget", "beneficiary_relation", "bank_partner"]`
- **Knowledge Retrieved (1 chunks)**:
  - [None] Score: `0.016393` | Source: `None` | Content: *"..."*
- **Citation**: `Darwix PH KB: ph_life_insurance_handbook.md (Ph Life Insurance Handbook — 3. Policy Lapse and Reinstatement Rules)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/philippines/eval_ph_case_3_mixed_language_1790921070_turn_1790921074534.mp3`

### Final Underwriting Profile
```json
{
  "applicant_name": null,
  "age": 31,
  "monthly_budget": null,
  "target_coverage": null,
  "insurance_type": "Darwix SecureTerm (Term Life)",
  "beneficiary_relation": null,
  "health_declaration": null,
  "bank_partner": null
}
```
