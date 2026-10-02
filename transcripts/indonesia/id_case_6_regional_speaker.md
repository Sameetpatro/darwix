# Indonesia Voice Bot Transcript

## Call Metadata
- **Case ID**: `id_case_6_regional_speaker`
- **Scenario Title**: Case 6: Regional Indonesian Speaker (Javanese & Sundanese Speech Patterns)
- **Description**: Customer uses East Javanese (piye, rek, monggo) and Sundanese (kumaha, teh, euy) dialect markers; agent comprehends directly without failure.
- **Market**: Indonesia (Consumer Finance / Multifinance)
- **Primary TTS Voice**: `id-ID-GadisNeural`
- **Session ID**: `eval_id_case_6_regional_speaker_1790921334`

---

## Conversation Transcript

### Turn 0 (Initial Bot Greeting)
**Vani**: "Halo! Selamat datang di Darwix Multifinance. Saya Vani, asisten digital Anda. Ada yang bisa kami bantu seputar cicilan atau pembayaran angsuran Anda?"

- **Language**: `id`
- **Dialect Style**: `colloquial`
### Turn 1
**Customer**: "Piye carane bayar angsuran iki rek? Monggo infone."

**Vani**: "Berdasarkan informasi resmi Darwix Multifinance:
# FAQ 2: Bagaimana cara membayar cicilan angsuran Darwix Multifinance?
- Jawaban: Pembayaran angsuran cicilan sangat mudah dan dapat dilakukan secara real-time melalui:
  1. Virtual Account Bank (BCA, Mandiri, BRI, BNI, Permata)."

#### Turn Metadata
- **Detected Language**: `id`
- **Dialect Style**: `regional`
- **Intent Detected**: `general_installment_inquiry`
- **Escalated to Human**: `False`
- **Support Path Offered**: `None`
- **Turn Latency**: `1672.9 ms` (TTS: `1659.8 ms`)
- **Account Context**: `{"contract_number": "DWX-ID-98234", "customer_name": "Budi Santoso", "product_type": "Sepeda Motor Honda Vario 160", "monthly_installment": 850000.0, "due_date_day": 10, "tenor_months": 24, "remaining_tenor": 14, "overdue_days": 0, "estimated_denda": 0.0, "support_path_offered": null}`
- **Knowledge Retrieved (1 chunks)**:
  - [None] Score: `0.016185` | Source: `None` | Content: *"..."*
- **Citation**: `Darwix ID KB: id_payment_faqs_objections.md (Id Payment Faqs Objections — FAQ 2: Bagaimana cara membayar cicilan angsuran Darwix Multifinance?)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/indonesia/eval_id_case_6_regional_speaker_1790921334_turn_1790921334093.mp3`

### Turn 2
**Customer**: "Kumaha lamun kuring hayang pelunasan dipercepat motor teh euy, aya diskon bunga teu?"

**Vani**: "Berdasarkan informasi resmi Darwix Multifinance:
# Fasilitas Pembiayaan yang Tersedia:
1. Pembiayaan Kendaraan Bermotor (Motor & Mobil):
   - Pembiayaan unit baru dan bekas berkualitas."

#### Turn Metadata
- **Detected Language**: `id`
- **Dialect Style**: `regional`
- **Intent Detected**: `early_payoff`
- **Escalated to Human**: `False`
- **Support Path Offered**: `None`
- **Turn Latency**: `5252.9 ms` (TTS: `5230.7 ms`)
- **Account Context**: `{"contract_number": "DWX-ID-98234", "customer_name": "Budi Santoso", "product_type": "Sepeda Motor Honda Vario 160", "monthly_installment": 850000.0, "due_date_day": 10, "tenor_months": 24, "remaining_tenor": 14, "overdue_days": 0, "estimated_denda": 0.0, "support_path_offered": null}`
- **Knowledge Retrieved (1 chunks)**:
  - [None] Score: `0.016393` | Source: `None` | Content: *"..."*
- **Citation**: `Darwix ID KB: id_multifinance_handbook.md (Id Multifinance Handbook — Fasilitas Pembiayaan yang Tersedia:)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/indonesia/eval_id_case_6_regional_speaker_1790921334_turn_1790921335776.mp3`

### Final Multifinance Account State
```json
{
  "contract_number": "DWX-ID-98234",
  "customer_name": "Budi Santoso",
  "product_type": "Sepeda Motor Honda Vario 160",
  "monthly_installment": 850000.0,
  "due_date_day": 10,
  "tenor_months": 24,
  "remaining_tenor": 14,
  "overdue_days": 0,
  "estimated_denda": 0.0,
  "support_path_offered": null
}
```
