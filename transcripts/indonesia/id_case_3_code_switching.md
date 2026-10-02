# Indonesia Voice Bot Transcript

## Call Metadata
- **Case ID**: `id_case_3_code_switching`
- **Scenario Title**: Case 3: Code-Switching Conversation (Indonesian + English Finance Terms)
- **Description**: Customer combines Indonesian syntax with English finance terminology (late fee, grace period, reschedule tenor).
- **Market**: Indonesia (Consumer Finance / Multifinance)
- **Primary TTS Voice**: `id-ID-GadisNeural`
- **Session ID**: `eval_id_case_3_code_switching_1790921219`

---

## Conversation Transcript

### Turn 0 (Initial Bot Greeting)
**Vani**: "Halo! Selamat datang di Darwix Multifinance. Saya Vani, asisten digital Anda. Ada yang bisa kami bantu seputar cicilan atau pembayaran angsuran Anda?"

- **Language**: `id`
- **Dialect Style**: `colloquial`
### Turn 1
**Customer**: "Siang kak, mau clarify soal cicilan mobil saya."

**Vani**: "Berdasarkan informasi resmi Darwix Multifinance:
# FAQ 1: Kalau saya telat bayar cicilan, ada denda atau late fee nggak?
- Jawaban: Ya, ada ketentuan denda jika melewati batas toleransi. Namun, Darwix memberikan masa tenggang (grace period) bebas denda selama 3 hari kalender setelah tanggal jatuh tempo. Jika pembayaran dilakukan setelah hari ke-3, denda dihitung sebesar 0,5% per hari dari nilai angsuran bulanan yang belum terbayar. Jika Anda bersedia melunasi angsuran pokok hari ini, tim kami dapat membantu mengajukan program keringanan penghapusan denda."

#### Turn Metadata
- **Detected Language**: `id`
- **Dialect Style**: `colloquial`
- **Intent Detected**: `general_installment_inquiry`
- **Escalated to Human**: `False`
- **Support Path Offered**: `None`
- **Turn Latency**: `2836.9 ms` (TTS: `2819.4 ms`)
- **Account Context**: `{"contract_number": "DWX-ID-98234", "customer_name": "Budi Santoso", "product_type": "Sepeda Motor Honda Vario 160", "monthly_installment": 850000.0, "due_date_day": 10, "tenor_months": 24, "remaining_tenor": 14, "overdue_days": 0, "estimated_denda": 0.0, "support_path_offered": null}`
- **Knowledge Retrieved (1 chunks)**:
  - [None] Score: `0.016393` | Source: `None` | Content: *"..."*
- **Citation**: `Darwix ID KB: id_payment_faqs_objections.md (Id Payment Faqs Objections — FAQ 1: Kalau saya telat bayar cicilan, ada denda atau late fee nggak?)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/indonesia/eval_id_case_3_code_switching_1790921219_turn_1790921219931.mp3`

### Turn 2
**Customer**: "Kalau saya telat bayar cicilan, ada late fee nggak? Dan apakah ada grace period sebelum kena penalty?"

**Vani**: "Kalau telat bayar, Darwix ada masa tenggang (grace period) bebas denda selama 3 hari kalender kok kak setelah tanggal jatuh tempo. Tapi kalau lewat dari 3 hari, baru kena denda keterlambatan 0,5% per hari dari nominal angsuran bulanan yang tertunggak ya."

#### Turn Metadata
- **Detected Language**: `id`
- **Dialect Style**: `code_switched`
- **Intent Detected**: `late_payment_fee`
- **Escalated to Human**: `False`
- **Support Path Offered**: `None`
- **Turn Latency**: `1527.0 ms` (TTS: `1506.9 ms`)
- **Account Context**: `{"contract_number": "DWX-ID-98234", "customer_name": "Budi Santoso", "product_type": "Sepeda Motor Honda Vario 160", "monthly_installment": 850000.0, "due_date_day": 10, "tenor_months": 24, "remaining_tenor": 14, "overdue_days": 0, "estimated_denda": 0.0, "support_path_offered": null}`
- **Knowledge Retrieved (1 chunks)**:
  - [None] Score: `0.016393` | Source: `None` | Content: *"..."*
- **Citation**: `Darwix ID KB: id_payment_faqs_objections.md (Id Payment Faqs Objections — FAQ 1: Kalau saya telat bayar cicilan, ada denda atau late fee nggak?)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/indonesia/eval_id_case_3_code_switching_1790921219_turn_1790921222771.mp3`

### Turn 3
**Customer**: "Bisa nggak kalau saya reschedule tenor angsuran saya jadi tiga puluh enam bulan?"

**Vani**: "Tentu bisa kak. Darwix Multifinance memiliki program restrukturisasi resmi yang diawasi OJK. Anda dapat mengajukan perpanjangan tenor pembiayaan agar beban nominal cicilan per bulan menjadi lebih ringan sesuai kemampuan."

#### Turn Metadata
- **Detected Language**: `id`
- **Dialect Style**: `code_switched`
- **Intent Detected**: `restructuring_inquiry`
- **Escalated to Human**: `False`
- **Support Path Offered**: `None`
- **Turn Latency**: `9511.1 ms` (TTS: `9465.5 ms`)
- **Account Context**: `{"contract_number": "DWX-ID-98234", "customer_name": "Budi Santoso", "product_type": "Sepeda Motor Honda Vario 160", "monthly_installment": 850000.0, "due_date_day": 10, "tenor_months": 24, "remaining_tenor": 14, "overdue_days": 0, "estimated_denda": 0.0, "support_path_offered": null}`
- **Knowledge Retrieved (1 chunks)**:
  - [None] Score: `0.016288` | Source: `None` | Content: *"..."*
- **Citation**: `Darwix ID KB: id_payment_faqs_objections.md (Id Payment Faqs Objections — Section 5)`
- **Turn Audio**: `/Users/sameetpatro/Desktop/darwix/recordings/indonesia/eval_id_case_3_code_switching_1790921219_turn_1790921224323.mp3`

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
