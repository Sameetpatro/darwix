# Philippines Voice Bot Transcript

## Call Metadata
- **Case ID**: `ph_case_4_human_escalation`
- **Scenario Title**: Case 4: Caller Requesting Human Assistance (Warm Transfer)
- **Description**: Caller asks complex estate planning questions and requests a human licensed financial advisor.
- **Market**: Philippines (Life Insurance / Bancassurance)
- **Primary TTS Voice**: `fil-PH-BlessicaNeural`
- **Session ID**: `eval_ph_case_4_human_escalation_1790921094`

---

## Conversation Transcript

### Turn 0 (Initial Bot Greeting)
**Vani**: "Magandang araw po! Welcome sa Darwix Life Bancassurance. Ako po si Vani, ang inyong insurance specialist. Nandito po ako para tulungan kayo sa life protection at bancassurance plans. Paano ko po kayo matutulungan today?"

- **Language**: `taglish`
### Turn 1
**Customer**: "Magandang araw po. May mga specific legal questions po ako tungkol sa trust fund at estate tax ng policy."

**Vani**: "Ilang taon na po kayo ngayon para ma-compute natin ang accurate rate?"

#### Turn Metadata
- **Detected Language / Dialect**: `taglish`
- **Intent Detected**: `general`
- **Escalated to Human**: `False`
- **Qualification Completed**: `False`
- **Turn Latency**: `1574.4 ms` (TTS: `1573.9 ms`)
- **Current Profile Slots**: `{"applicant_name": null, "age": null, "monthly_budget": null, "target_coverage": null, "insurance_type": null, "beneficiary_relation": null, "health_declaration": null, "bank_partner": null}`
- **Missing Slots**: `["age", "target_coverage", "monthly_budget", "beneficiary_relation", "bank_partner"]`
- **Knowledge Retrieved**: `None (Deterministic Underwriting / Direct Intent Logic)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/philippines/eval_ph_case_4_human_escalation_1790921094_turn_1790921094945.mp3`

### Turn 2
**Customer**: "Pwede po bang kumausap ng live agent or licensed financial advisor ngayon?"

**Vani**: "Sige po! Ikokonekta ko po kayo agad sa isa sa aming licensed Financial Advisors sa Darwix Life Bancassurance. Sandali lamang po habang inililipat ko ang inyong tawag para matulungan kayo personally."

#### Turn Metadata
- **Detected Language / Dialect**: `taglish`
- **Intent Detected**: `human_escalation`
- **Escalated to Human**: `True`
- **Qualification Completed**: `False`
- **Turn Latency**: `1984.8 ms` (TTS: `1984.2 ms`)
- **Current Profile Slots**: `{"applicant_name": null, "age": null, "monthly_budget": null, "target_coverage": null, "insurance_type": null, "beneficiary_relation": null, "health_declaration": null, "bank_partner": null}`
- **Missing Slots**: `["age", "target_coverage", "monthly_budget", "beneficiary_relation", "bank_partner"]`
- **Knowledge Retrieved**: `None (Deterministic Underwriting / Direct Intent Logic)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/philippines/eval_ph_case_4_human_escalation_1790921094_turn_1790921096519.mp3`

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
