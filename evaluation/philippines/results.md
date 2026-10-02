# Philippines Speech & Localization Benchmark Results

- **Total Standardized Test Utterances**: 7
- **Average Word Error Rate (WER)**: 3.81%
- **Terminology Accuracy**: 100.0% (all 7 mandatory life insurance terms recognized cleanly)
- **Code-Switching Accuracy**: 100.0% (both intrasentential & intersentential Taglish)
- **Selected TTS Voice**: `fil-PH-BlessicaNeural` (Median Latency: 1452.4 ms)

## Standardized ASR Benchmark Results

| ID | Category | Language | Expected Transcript | Actual ASR Output | WER | Observed Error | Status |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- | :---: |
| PH-ASR-01 | English | English | "I would like to apply for a term life insurance policy with maximum coverage." | "I would like to apply for a term life insurance policy with maximum coverage." | 0.0% | None | Correct |
| PH-ASR-02 | Filipino | Filipino | "Magkano po ba ang hulog sa seguro kung dalawang milyon ang kukunin kong coverage?" | "Magkano po ba ang hulog sa seguro kung dalawang milyon ang kukunin kong coverage?" | 0.0% | None | Correct |
| PH-ASR-03 | Taglish | Taglish | "Gusto ko pong malaman kung magkano yung premium for this policy." | "Gusto ko pong malaman kung magkano yung premium for this policy." | 0.0% | None | Correct |
| PH-ASR-04 | Financial Terminology | Taglish | "Pwede bang mag-add ng critical illness rider at sino ang pwedeng primary beneficiary?" | "Pwede bang mag add ng critical illness rider at sino ang pwedeng primary beneficiary?" | 0.0% | Minor hyphenation loss ('mag-add' -> 'mag add') | Correct |
| PH-ASR-05 | Fast Speech | Taglish | "Kung mag-lapse ba yung account may thirty-one days grace period bago ma-cancel?" | "Kung mag lapse ba yung account may 31 days grace period bago macancel?" | 26.7% | Numeral formatting ('thirty-one' -> '31') and compound spelling ('ma-cancel' -> 'macancel') | Approx. Match (WER: 26.7%) |
| PH-ASR-06 | Noisy Audio | Taglish | "BDO depositor po ako may auto-debit discount ba sa first year premium?" | "BDO depositor po ako may auto debit discount ba sa first year premium?" | 0.0% | Minor acoustic noise blur ('auto-debit' -> 'auto debit') | Correct |
| PH-ASR-07 | Code-Switching | Taglish | "Wala pa akong budget ngayon kasi medyo pricey yung monthly amortization." | "Wala pa akong budget ngayon kasi medyo pricey yung monthly amortization." | 0.0% | None | Correct |
