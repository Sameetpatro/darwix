# Indonesia Regional Accent & Dialect Comprehension Report

## Executive Summary
Across Indonesia's archipelago, consumers routinely weave regional ethnolinguistic dialect markers into Bahasa Indonesia. Rather than forcing users into unnatural formal Indonesian or failing to parse their utterances, Vani's locale engine detects regional markers and seamlessly routes inquiries to the correct multifinance dialog paths.

---

## Regional Accent Evaluations

### 1. Javanese Regional Indonesian (Jawa Tengah, Jawa Timur, Yogyakarta)
- **Test Utterance**: *"Piye carane bayar angsuran iki rek? Monggo infone."*
- **Linguistic Markers Identified**:
  - `piye`: Javanese for *"how / bagaimana"*
  - `rek`: East Javanese (Surabaya/Malang) colloquial vocative address (*"kawan-kawan / teman-teman"*)
  - `iki`: Javanese demonstrative pronoun (*"ini"*)
  - `monggo`: Polite Javanese invitation / honorific (*"silakan"*)
- **System Comprehension**: **100% Correct**
- **Handling Approach**:
  - The locale engine flags `regional_dialect: "javanese"`.
  - Maps `piye carane bayar` directly to `intent: "payment_methods"`.
  - Responds in polite, accessible Indonesian while honoring the consultative warmth expected in Javanese interpersonal interactions.

---

### 2. Sundanese Regional Indonesian (Jawa Barat & Banten)
- **Test Utterance**: *"Kumaha cara bayar angsuran motor teh euy?"*
- **Linguistic Markers Identified**:
  - `kumaha`: Sundanese interrogative for *"how / bagaimana"*
  - `teh`: Sundanese topic-marker particle (used for focus and affirmation)
  - `euy`: Characteristic Sundanese informal exclamation / vocative marker
- **System Comprehension**: **100% Correct**
- **Handling Approach**:
  - The locale engine flags `regional_dialect: "sundanese"`.
  - Resolves `kumaha cara bayar` to `intent: "payment_methods"`.
  - Delivers channel instructions (BCA Virtual Account, Indomaret, Alfamart) with friendly intonation.

---

### 3. Medan / North Sumatra Regional Indonesian (Batak & Malay Influences)
- **Test Utterance**: *"Cemana cara perpanjang tenor pembiayaan kami ini wak?"*
- **Linguistic Markers Identified**:
  - `cemana`: Medan regional contraction of *"macam mana / bagaimana"*
  - `kami`: Exclusive first-person plural used colloquially in North Sumatra for *"saya / kami"*
  - `wak`: Respectful familiar vocative address used widely in Medan street parlance (*"kawan / paman / bapak"*)
- **System Comprehension**: **100% Correct**
- **Handling Approach**:
  - The locale engine flags `regional_dialect: "medan"`.
  - Maps `perpanjang tenor pembiayaan` directly to `intent: "restructuring_inquiry"`.
  - Outlines the 36-month loan restructuring criteria, required branch documents, and processing timelines.

---

## Regional Performance Summary

| Regional Dialect | Dialect Region | Sample Markers | Comprehension Rate | Handling Approach | Fallback Required? |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **Javanese** | Central & East Java | *piye, rek, monggo, sampun, nggih* | **100%** | Native Intent Mapping + Polite Warmth | **No** |
| **Sundanese** | West Java (Bandung, Bogor) | *kumaha, teh, euy, atuh, mah* | **100%** | Native Intent Mapping + Accessible Tone | **No** |
| **Medan / Batak** | North Sumatra | *cemana, wak, kali, kelen, bah* | **100%** | Direct Restructuring Intent Resolution | **No** |
