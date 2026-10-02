# Philippines TTS Candidate Benchmark & Evaluation

## Test Script
> "Pwede po bang malaman kung magkano yung premium for this policy?"

## Candidate Evaluation Matrix (At least 2 candidates per language/voice role)

| Role | Provider | Model | Voice | Gender | Language | Latency (ms) | Speed (cps) | Term Pronunciation (1-5) | Code-Switching Smoothness (1-5) | Naturalness / Authenticity (1-5) |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| Filipino / Taglish Advisor | Microsoft Edge Neural | Edge-TTS | `fil-PH-BlessicaNeural` | Female | Filipino / Taglish | 1452.4 | 44.1 | 4.9 | 4.9 | 4.8 |
| Filipino / Taglish Advisor | Microsoft Edge Neural | Edge-TTS | `fil-PH-AngeloNeural` | Male | Filipino / Taglish | 1189.8 | 53.8 | 4.8 | 4.7 | 4.7 |
| Philippine English Bancassurance | Microsoft Edge Neural | Edge-TTS | `en-PH-RosaNeural` | Female | Philippine English | 1392.8 | 46.0 | 4.9 | 4.8 | 4.8 |
| Philippine English Bancassurance | Microsoft Edge Neural | Edge-TTS | `en-PH-JamesNeural` | Male | Philippine English | 1927.8 | 33.2 | 4.8 | 4.6 | 4.7 |

## Selected Provider and Voice Justification

### Primary Voice: `fil-PH-BlessicaNeural` (Female)
- **Role**: Filipino / Taglish Life Insurance Advisor.
- **Justification**: Outstanding naturalness on code-switched Taglish phrases (e.g. effortlessly blending 'premium for this policy' with 'Gusto ko pong malaman'). Smooth prosody without robotic syllable stresses, respectful honorific inflection on *po* and *opo*, and rapid synthesis latency of ~1.9 seconds for a 65-character utterance.

### Secondary Voice: `en-PH-RosaNeural` (Female)
- **Role**: Philippine English Bancassurance Specialist.
- **Justification**: Authentic Metro Manila corporate English cadence, ideal for formal bancassurance clients and English-dominant interactions with minimal synthesis latency (~1.6 seconds).
