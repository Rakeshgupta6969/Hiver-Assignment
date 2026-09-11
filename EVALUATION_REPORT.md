# Formal Evaluation Report: Hiver AI Customer Support Agent

**Date of Evaluation:** 2026-09-11  
**Total Benchmark Test Cases:** 50  
**Evaluation Mode:** Deterministic Semantic & Grounded RAG Pipeline  

---

## 1. Executive Summary

This evaluation report benchmarks the performance of the **Hiver AI Customer Support Agent** against the standardized **Golden Evaluation Set** (`data/golden_evaluation_set.json`). The agent was evaluated across all three required tasks:
1. **Intent Classification**: Classifying customer inquiries into 6 distinct categories.
2. **Response Generation**: Grounding generated responses in historical brand support resolutions via ChromaDB RAG.
3. **Automation Decision**: Triaging between autonomous resolution (`AUTOMATE`) vs human routing (`ESCALATE_TO_HUMAN`) with explainable reasoning.

### Key High-Level Results

| Metric | Result | Target Benchmark | Status |
| :--- | :--- | :--- | :--- |
| **Overall Intent Classification Accuracy** | **88.0%** | > 85.0% | **EXCEEDED** |
| **Automation Gate Decision Accuracy** | **94.0%** | > 85.0% | **EXCEEDED** |
| **High-Risk False Automations** | **0** | **0 (Zero Tolerance)** | **VERIFIED** |
| **Mean End-to-End Latency** | **537.36 ms** | < 1,000 ms | **EXCEEDED** |
| **P95 Latency** | **642.62 ms** | < 2,000 ms | **EXCEEDED** |

---

## 2. Intent Classification Performance Breakdown

| Intent Category | Support (Count) | Precision | Recall | F1-Score |
| :--- | :--- | :--- | :--- | :--- |
| `ORDER_DELIVERY_ISSUE` | 8 | 87.5% | 87.5% | 87.5% |
| `BILLING_REFUND_INQUIRY` | 11 | 91.7% | 100.0% | 95.7% |
| `TECHNICAL_PRODUCT_SUPPORT` | 10 | 100.0% | 80.0% | 88.9% |
| `ACCOUNT_SECURITY_ACCESS` | 5 | 62.5% | 100.0% | 76.9% |
| `POLICY_GENERAL_FAQ` | 8 | 85.7% | 75.0% | 80.0% |
| `COMPLAINT_FEEDBACK_ESCALATION` | 8 | 100.0% | 87.5% | 93.3% |

---

## 3. Intent Confusion Matrix

The rows represent the Ground Truth intent, while the columns represent the Model Predictions:

| Ground Truth \ Pred | ORD | BIL | TEC | SEC | FAQ | ESC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ORD (ORDER_DELIVERY_ISSUE)** | 7 | 0 | 0 | 1 | 0 | 0 |
| **BIL (BILLING_REFUND_INQUIRY)** | 0 | 11 | 0 | 0 | 0 | 0 |
| **TEC (TECHNICAL_PRODUCT_SUPPORT)** | 0 | 0 | 8 | 2 | 0 | 0 |
| **SEC (ACCOUNT_SECURITY_ACCESS)** | 0 | 0 | 0 | 5 | 0 | 0 |
| **FAQ (POLICY_GENERAL_FAQ)** | 1 | 1 | 0 | 0 | 6 | 0 |
| **ESC (COMPLAINT_FEEDBACK_ESCALATION)** | 0 | 0 | 0 | 0 | 1 | 7 |

---

## 4. Automation Safety & Triage Analysis

In customer support automation, **False Automation** (sending an automated brush-off to a customer in crisis or with a security breach) carries severe consequences:
- **Zero False Automation**: In all test cases requiring human intervention (such as legal threats, passenger safety incidents, account compromise, and card number exposure), the automation gatekeeper achieved **100% precision in human escalation**.
- **Accidental PII Protection**: When customers accidentally tweeted full credit card numbers, phone numbers, or email addresses, the preprocessor detected and masked the sensitive information, and the gatekeeper immediately escalated the ticket to `Privacy & Data Protection Specialist`.
- **Audit Trail Logging**: Every decision was recorded in `logs/decision_audit.jsonl` with timestamps, confidence scores, and natural language justifications.

---

## 5. Granular Benchmark Case Results

| ID | Category | Expected Intent | Predicted Intent | Decision | Latency | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GOLD_01` | standard | `ORDER_DELIVERY_ISSUE` | `ORDER_DELIVERY_ISSUE` | `AUTOMATE` | 797.12 ms | **PASS** |
| `GOLD_02` | standard | `POLICY_GENERAL_FAQ` | `POLICY_GENERAL_FAQ` | `AUTOMATE` | 573.67 ms | **PASS** |
| `GOLD_03` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `TECHNICAL_PRODUCT_SUPPORT` | `AUTOMATE` | 569.23 ms | **PASS** |
| `GOLD_04` | standard | `POLICY_GENERAL_FAQ` | `POLICY_GENERAL_FAQ` | `AUTOMATE` | 562.99 ms | **PASS** |
| `GOLD_05` | standard | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 558.57 ms | **PASS** |
| `GOLD_06` | standard | `ACCOUNT_SECURITY_ACCESS` | `ACCOUNT_SECURITY_ACCESS` | `ESCALATE_TO_HUMAN` | 525.91 ms | **PASS** |
| `GOLD_07` | crisis_escalation | `COMPLAINT_FEEDBACK_ESCALATION` | `COMPLAINT_FEEDBACK_ESCALATION` | `ESCALATE_TO_HUMAN` | 543.69 ms | **PASS** |
| `GOLD_08` | crisis_escalation | `COMPLAINT_FEEDBACK_ESCALATION` | `COMPLAINT_FEEDBACK_ESCALATION` | `ESCALATE_TO_HUMAN` | 516.45 ms | **PASS** |
| `GOLD_09` | standard | `ACCOUNT_SECURITY_ACCESS` | `ACCOUNT_SECURITY_ACCESS` | `ESCALATE_TO_HUMAN` | 553.35 ms | **PASS** |
| `GOLD_10` | pii_leak | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 537.07 ms | **PASS** |
| `GOLD_11` | standard | `ORDER_DELIVERY_ISSUE` | `ORDER_DELIVERY_ISSUE` | `AUTOMATE` | 537.92 ms | **PASS** |
| `GOLD_12` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `TECHNICAL_PRODUCT_SUPPORT` | `AUTOMATE` | 545.03 ms | **PASS** |
| `GOLD_13` | standard | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `AUTOMATE` | 525.36 ms | **PASS** |
| `GOLD_14` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `TECHNICAL_PRODUCT_SUPPORT` | `AUTOMATE` | 642.62 ms | **PASS** |
| `GOLD_15` | crisis_escalation | `COMPLAINT_FEEDBACK_ESCALATION` | `COMPLAINT_FEEDBACK_ESCALATION` | `ESCALATE_TO_HUMAN` | 529.39 ms | **PASS** |
| `GOLD_16` | pii_leak | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 515.55 ms | **PASS** |
| `GOLD_17` | standard | `POLICY_GENERAL_FAQ` | `POLICY_GENERAL_FAQ` | `AUTOMATE` | 532.18 ms | **PASS** |
| `GOLD_18` | standard | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `AUTOMATE` | 514.08 ms | **PASS** |
| `GOLD_19` | crisis_escalation | `COMPLAINT_FEEDBACK_ESCALATION` | `COMPLAINT_FEEDBACK_ESCALATION` | `ESCALATE_TO_HUMAN` | 517.68 ms | **PASS** |
| `GOLD_20` | standard | `ACCOUNT_SECURITY_ACCESS` | `ACCOUNT_SECURITY_ACCESS` | `ESCALATE_TO_HUMAN` | 568.36 ms | **PASS** |
| `GOLD_21` | standard | `ORDER_DELIVERY_ISSUE` | `ORDER_DELIVERY_ISSUE` | `AUTOMATE` | 596.7 ms | **PASS** |
| `GOLD_22` | standard | `POLICY_GENERAL_FAQ` | `POLICY_GENERAL_FAQ` | `AUTOMATE` | 526.31 ms | **PASS** |
| `GOLD_23` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `TECHNICAL_PRODUCT_SUPPORT` | `AUTOMATE` | 536.43 ms | **PASS** |
| `GOLD_24` | standard | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 529.6 ms | **PASS** |
| `GOLD_25` | standard | `POLICY_GENERAL_FAQ` | `ORDER_DELIVERY_ISSUE` | `ESCALATE_TO_HUMAN` | 522.56 ms | **FAIL** |
| `GOLD_26` | standard | `ORDER_DELIVERY_ISSUE` | `ORDER_DELIVERY_ISSUE` | `AUTOMATE` | 607.93 ms | **PASS** |
| `GOLD_27` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `TECHNICAL_PRODUCT_SUPPORT` | `AUTOMATE` | 523.17 ms | **PASS** |
| `GOLD_28` | standard | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 540.4 ms | **PASS** |
| `GOLD_29` | standard | `ORDER_DELIVERY_ISSUE` | `ORDER_DELIVERY_ISSUE` | `AUTOMATE` | 521.36 ms | **PASS** |
| `GOLD_30` | pii_leak | `ORDER_DELIVERY_ISSUE` | `ACCOUNT_SECURITY_ACCESS` | `ESCALATE_TO_HUMAN` | 498.33 ms | **FAIL** |
| `GOLD_31` | standard | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 503.11 ms | **FAIL** |
| `GOLD_32` | standard | `POLICY_GENERAL_FAQ` | `BILLING_REFUND_INQUIRY` | `AUTOMATE` | 511.04 ms | **FAIL** |
| `GOLD_33` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `ACCOUNT_SECURITY_ACCESS` | `ESCALATE_TO_HUMAN` | 521.37 ms | **FAIL** |
| `GOLD_34` | crisis_escalation | `COMPLAINT_FEEDBACK_ESCALATION` | `COMPLAINT_FEEDBACK_ESCALATION` | `ESCALATE_TO_HUMAN` | 503.4 ms | **PASS** |
| `GOLD_35` | standard | `ORDER_DELIVERY_ISSUE` | `ORDER_DELIVERY_ISSUE` | `AUTOMATE` | 508.16 ms | **PASS** |
| `GOLD_36` | pii_leak | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 521.75 ms | **PASS** |
| `GOLD_37` | pii_leak | `TECHNICAL_PRODUCT_SUPPORT` | `ACCOUNT_SECURITY_ACCESS` | `ESCALATE_TO_HUMAN` | 651.08 ms | **FAIL** |
| `GOLD_38` | standard | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 545.59 ms | **PASS** |
| `GOLD_39` | standard | `ORDER_DELIVERY_ISSUE` | `ORDER_DELIVERY_ISSUE` | `AUTOMATE` | 516.49 ms | **PASS** |
| `GOLD_40` | standard | `BILLING_REFUND_INQUIRY` | `BILLING_REFUND_INQUIRY` | `ESCALATE_TO_HUMAN` | 521.04 ms | **PASS** |
| `GOLD_41` | crisis_escalation | `COMPLAINT_FEEDBACK_ESCALATION` | `COMPLAINT_FEEDBACK_ESCALATION` | `ESCALATE_TO_HUMAN` | 507.98 ms | **PASS** |
| `GOLD_42` | crisis_escalation | `COMPLAINT_FEEDBACK_ESCALATION` | `COMPLAINT_FEEDBACK_ESCALATION` | `ESCALATE_TO_HUMAN` | 518.26 ms | **PASS** |
| `GOLD_43` | crisis_escalation | `COMPLAINT_FEEDBACK_ESCALATION` | `POLICY_GENERAL_FAQ` | `ESCALATE_TO_HUMAN` | 501.88 ms | **FAIL** |
| `GOLD_44` | standard | `POLICY_GENERAL_FAQ` | `POLICY_GENERAL_FAQ` | `AUTOMATE` | 510.68 ms | **PASS** |
| `GOLD_45` | standard | `POLICY_GENERAL_FAQ` | `POLICY_GENERAL_FAQ` | `AUTOMATE` | 537.26 ms | **PASS** |
| `GOLD_46` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `TECHNICAL_PRODUCT_SUPPORT` | `AUTOMATE` | 506.97 ms | **PASS** |
| `GOLD_47` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `TECHNICAL_PRODUCT_SUPPORT` | `AUTOMATE` | 535.36 ms | **PASS** |
| `GOLD_48` | standard | `TECHNICAL_PRODUCT_SUPPORT` | `TECHNICAL_PRODUCT_SUPPORT` | `AUTOMATE` | 468.97 ms | **PASS** |
| `GOLD_49` | standard | `ACCOUNT_SECURITY_ACCESS` | `ACCOUNT_SECURITY_ACCESS` | `ESCALATE_TO_HUMAN` | 448.83 ms | **PASS** |
| `GOLD_50` | standard | `ACCOUNT_SECURITY_ACCESS` | `ACCOUNT_SECURITY_ACCESS` | `ESCALATE_TO_HUMAN` | 459.83 ms | **PASS** |

---

## 6. Conclusion

The evaluation confirms that the Hiver AI Customer Support Agent operates with high accuracy, sub-second latency, grounded response consistency, and safety guardrails, fulfilling all evaluation criteria for the Hiver SDE Intern take-home assignment.