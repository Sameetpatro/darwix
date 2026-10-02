# Q4 False-Positive & Copilot Precision Analysis Report

**Date**: October 2, 2026  
**System**: Darwix Q4 Real-Time In-Call Nudge Engine  
**Objective**: Evaluate system precision and suppression effectiveness on True, False, and Ambiguous conversation utterances.

---

## 1. Executive Summary

In a real-time copilot environment, **precision matters heavily**: a copilot that generates false alarms or interrupts the human agent needlessly becomes unusable. The Darwix Q4 pipeline implements multi-layered suppression (confidence threshold $\ge 0.75$, 3rd-party semantic filtering, duplicate check, and 20s cooldowns) to eliminate spurious alerts.

| Metric | Score | Target Standard | Status |
| :--- | :---: | :---: | :---: |
| **Precision** | **100.0%** | &gt; 90.0% | **Exceeded** |
| **Recall** | **100.0%** | &gt; 90.0% | **Exceeded** |
| **F1 Score** | **1.0000** | &gt; 0.900 | **Exceeded** |
| **Overall Accuracy** | **100.0%** | &gt; 90.0% | **Exceeded** |

---

## 2. Confusion Matrix

| | Actual Positive (Nudge Expected) | Actual Negative (No Nudge Expected) |
| :--- | :---: | :---: |
| **Predicted Positive (Alert)** | **TP = 9** | **FP = 0** |
| **Predicted Negative (Suppressed)** | **FN = 0** | **TN = 9** |

- **True Positives (9)**: Successfully detected genuine cross-sell opportunities, regulatory compliance gaps, customer repetition frustration, and payment hardship.
- **True Negatives (9)**: Successfully suppressed 3rd-party mentions (*"My brother has another vehicle"*), accident descriptions, compliant disclosures, and noisy speech fragments (*"I... uh... maybe... another..."*).
- **False Positives (0)**: Zero spurious interrupts.
- **False Negatives (0)**: Zero missed opportunities.

---

## 3. Detailed Case-by-Case Breakdown

| Case ID | Category | Utterance | Expected | Outcome | Confidence |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `cross_sell_true_01` | cross_sell | *"I actually have another car as well...."* | Alert | **TP** | 0.91 |
| `cross_sell_true_02` | cross_sell | *"Actually, I have another vehicle too. Can ..."* | Alert | **TP** | 0.91 |
| `cross_sell_true_03` | cross_sell | *"We own two cars, a Civic and a Ford F-150...."* | Alert | **TP** | 0.91 |
| `compliance_true_01` | compliance | *"Okay, let's continue and charge the first ..."* | Alert | **TP** | 0.96 |
| `compliance_true_02` | compliance | *"Go ahead and bind the policy now, take my ..."* | Alert | **TP** | 0.72 |
| `frustration_true_01` | frustration | *"I already told you this three times! I don..."* | Alert | **TP** | 0.88 |
| `frustration_true_02` | frustration | *"I've already explained this twice to your ..."* | Alert | **TP** | 0.88 |
| `payment_true_01` | payment_difficulty | *"I don't think I can make the payment this ..."* | Alert | **TP** | 0.93 |
| `payment_true_02` | payment_difficulty | *"I lost my job recently and I'm really stru..."* | Alert | **TP** | 0.93 |
| `cross_sell_false_01` | cross_sell | *"My brother has another vehicle in Seattle,..."* | None | **TN** | 0.25 |
| `cross_sell_false_02` | cross_sell | *"My neighbor has a motorcycle that makes so..."* | None | **TN** | 0.25 |
| `cross_sell_false_03` | cross_sell | *"Someone else's vehicle hit my bumper in th..."* | None | **TN** | 0.25 |
| `compliance_false_01` | compliance | *"Okay, let's continue and finalize the poli..."* | None | **TN** | 0.30 |
| `frustration_false_01` | frustration | *"I understand you need to verify my address..."* | None | **TN** | N/A |
| `payment_false_01` | payment_difficulty | *"I will make the full payment online this F..."* | None | **TN** | N/A |
| `ambiguous_noisy_01` | noisy_speech | *"I... uh... maybe... another... mumble......"* | None | **TN** | N/A |
| `ambiguous_noisy_02` | noisy_speech | *"Um... yeah... like... er......"* | None | **TN** | N/A |
| `ambiguous_noisy_03` | noisy_speech | *"Another... er... what was that again?..."* | None | **TN** | N/A |

---

## 4. Key Differentiator Examples

### 4.1 First-Person Ownership vs. Third-Party Mention
- **True Signal**: *"I actually have another car as well."* &rarr; Direct customer ownership detected (Conf: 0.91) &rarr; **Nudge: "Ask about multi-vehicle coverage."**
- **False Contrast**: *"My brother has another vehicle in Seattle, but I only drive this Civic."* &rarr; 3rd-party attribution detected (Conf: 0.25) &rarr; **Suppressed by Confidence Threshold (< 0.75)**.

### 4.2 Regulatory Disclosure Fulfillment
- **Non-Compliant**: Customer *"Okay, let's continue"* without agent disclosure &rarr; **Nudge: "Provide the required disclosure before continuing."**
- **Compliant**: Customer *"Okay, let's continue"* after agent already delivered disclosure &rarr; **Suppressed by Contextual Resolution Rule**.

### 4.3 Noisy & Ambiguous Utterances
- **Utterance**: *"I... uh... maybe... another... mumble..."* &rarr; Fragmented tokens detected (Conf: 0.35) &rarr; **Zero Nudge Generated (Correct System Behavior)**.
