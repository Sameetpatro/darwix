# Indonesia Speech & Localization Benchmark Results

- **Total Standardized Test Utterances**: 9
- **Average Word Error Rate (WER)**: 6.98%
- **Terminology Accuracy**: 100.0% (all 7 mandatory multifinance terms recognized cleanly)
- **Regional Accent Comprehension**: 100.0% (Javanese, Sundanese, Medan regional dialects)
- **Selected TTS Voice**: `id-ID-GadisNeural` (Median Latency: 1351.9 ms)

## Standardized ASR Benchmark Results

| ID | Category | Language | Expected Transcript | Actual ASR Output | WER | Observed Error | Status |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: |
| ID-ASR-01 | Formal Indonesian | Formal Indonesian | "Selamat siang, saya ingin menanyakan perihal ketentuan pembayaran denda keterlambatan angsuran pembiayaan saya." | "Selamat siang, saya ingin menanyakan perihal ketentuan pembayaran denda keterlambatan angsuran pembiayaan saya." | 0.0% | None | Correct |
| ID-ASR-02 | Colloquial Indonesian | Colloquial Indonesian | "Halo kak, mau nanya dong soal cicilan motor saya yang jatuh tempo besok gimana ya?" | "Halo kak, mau nanya dong soal cicilan motor saya yang jatuh tempo besok gimana ya?" | 0.0% | None | Correct |
| ID-ASR-03 | Indonesian + English (Code-Switching) | Code-Switched Indonesian | "Kalau saya telat bayar cicilan, ada late fee nggak?" | "Kalau saya telat bayar cicilan, ada late fee nggak?" | 0.0% | None | Correct |
| ID-ASR-04 | Finance Terminology | Indonesian | "Berapa minimal DP untuk pembiayaan motor ini dengan tenor dua puluh empat bulan?" | "Berapa minimal DP untuk pembiayaan motor ini dengan tenor 24 bulan?" | 23.1% | Numeral formatting ('dua puluh empat' -> '24') | Approx. Match (WER: 23.1%) |
| ID-ASR-05 | Fast Speech | Colloquial Indonesian | "Bisa tolong reschedule tenor angsuran saya jadi tiga puluh enam bulan nggak kak?" | "Bisa tolong reschedule tenor angsuran saya jadi 36 bulan nggak kak?" | 23.1% | Digit representation ('tiga puluh enam' -> '36') | Approx. Match (WER: 23.1%) |
| ID-ASR-06 | Noisy Audio | Colloquial Indonesian | "Denda-nya terlalu tinggi kak, bisa minta waiver atau potongan denda nggak?" | "Dendanya terlalu tinggi kak, bisa minta waiver atau potongan denda nggak?" | 16.7% | Hyphen normalization ('denda-nya' -> 'dendanya') | Approx. Match (WER: 16.7%) |
| ID-ASR-07 | Regional Accent (Javanese) | Regional Indonesian (Javanese) | "Piye carane bayar angsuran iki rek? Monggo infone." | "Piye carane bayar angsuran iki rek? Monggo infone." | 0.0% | None | Correct |
| ID-ASR-08 | Regional Accent (Sundanese) | Regional Indonesian (Sundanese) | "Kumaha cara bayar angsuran motor teh euy?" | "Kumaha cara bayar angsuran motor teh euy?" | 0.0% | None | Correct |
| ID-ASR-09 | Regional Accent (Medan / Batak) | Regional Indonesian (Medan) | "Cemana cara perpanjang tenor pembiayaan kami ini wak?" | "Cemana cara perpanjang tenor pembiayaan kami ini wak?" | 0.0% | None | Correct |
