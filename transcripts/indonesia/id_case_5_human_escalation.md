# Indonesia Voice Bot Transcript

## Call Metadata
- **Case ID**: `id_case_5_human_escalation`
- **Scenario Title**: Case 5: Caller Requesting Human Assistance (Warm Transfer)
- **Description**: Customer inquires about total loss vehicle insurance dispute and requests immediate transfer to customer service debt counselor.
- **Market**: Indonesia (Consumer Finance / Multifinance)
- **Primary TTS Voice**: `id-ID-GadisNeural`
- **Session ID**: `eval_id_case_5_human_escalation_1790921310`

---

## Conversation Transcript

### Turn 0 (Initial Bot Greeting)
**Vani**: "Halo! Selamat datang di Darwix Multifinance. Saya Vani, asisten digital Anda. Ada yang bisa kami bantu seputar cicilan atau pembayaran angsuran Anda?"

- **Language**: `id`
- **Dialect Style**: `colloquial`
### Turn 1
**Customer**: "Halo, selamat siang."

**Vani**: "Mohon maaf Bapak/Ibu, saya belum memiliki informasi yang valid mengenai hal tersebut saat ini. Jika berkenan, saya dapat menghubungkan Anda dengan petugas customer service kami untuk bantuan lebih lanjut."

#### Turn Metadata
- **Detected Language**: `id`
- **Dialect Style**: `formal`
- **Intent Detected**: `unsupported`
- **Escalated to Human**: `False`
- **Support Path Offered**: `None`
- **Turn Latency**: `4227.0 ms` (TTS: `4226.2 ms`)
- **Account Context**: `{"contract_number": "DWX-ID-98234", "customer_name": "Budi Santoso", "product_type": "Sepeda Motor Honda Vario 160", "monthly_installment": 850000.0, "due_date_day": 10, "tenor_months": 24, "remaining_tenor": 14, "overdue_days": 0, "estimated_denda": 0.0, "support_path_offered": null}`
- **Knowledge Retrieved**: `None (Deterministic Installment Context / Direct Intent Logic)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/indonesia/eval_id_case_5_human_escalation_1790921310_turn_1790921310768.mp3`

### Turn 2
**Customer**: "Saya ada masalah sengketa klaim asuransi total loss kendaraan saya, bisa tolong sambungkan ke staf manusia atau customer service debt counselor sekarang?"

**Vani**: "Siap kak! Saya langsung sambungkan panggilan kakak ke Customer Service Darwix Multifinance ya. Ditunggu sebentar ya kak, panggilan sedang dialihkan."

#### Turn Metadata
- **Detected Language**: `id`
- **Dialect Style**: `code_switched`
- **Intent Detected**: `human_escalation`
- **Escalated to Human**: `True`
- **Support Path Offered**: `None`
- **Turn Latency**: `1800.8 ms` (TTS: `1799.6 ms`)
- **Account Context**: `{"contract_number": "DWX-ID-98234", "customer_name": "Budi Santoso", "product_type": "Sepeda Motor Honda Vario 160", "monthly_installment": 850000.0, "due_date_day": 10, "tenor_months": 24, "remaining_tenor": 14, "overdue_days": 0, "estimated_denda": 0.0, "support_path_offered": null}`
- **Knowledge Retrieved**: `None (Deterministic Installment Context / Direct Intent Logic)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/indonesia/eval_id_case_5_human_escalation_1790921310_turn_1790921314995.mp3`

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
