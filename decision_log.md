# Decision Log: Architecture, Triage Policies & Audit Trail

This document details the **Architectural Decision Records (ADRs)**, **Automation & Escalation Policies**, and the **Decision Audit Trail Schema** implemented in the **Hiver AI Customer Support Agent**.

---

## 1. Architectural Decision Records (ADRs)

### ADR-01: In-Process Vector Database (ChromaDB with Local ONNX Embeddings)
* **Context**: The agent requires Retrieval-Augmented Generation (RAG) over historical Twitter customer support interactions to ground generated replies and calculate semantic precedent similarity.
* **Decision**: Selected **ChromaDB** configured with local in-process persistence and the ONNX-optimized `all-MiniLM-L6-v2` embedding model.
* **Rationale**:
  1. *Zero External Infrastructure*: Eliminates dependencies on external managed vector DB services (e.g., Pinecone, Weaviate), allowing reviewers and automated CI environments to run the entire pipeline instantly without setup credentials.
  2. *Low Latency*: Sub-millisecond vector indexing and retrieval directly in-memory, achieving end-to-end response times under 400ms.
  3. *Metadata Filtering*: Supports strict filtered queries (`where={"intent": intent_name}`) with dynamic fallback to unfiltered similarity search when filtered density is low.
* **Alternatives Considered**:
  - *FAISS*: Faster for millions of vectors, but lacks native metadata persistence and document management out of the box.
  - *Cloud Vector DBs*: High operational overhead, network latency, and credential management barriers for reviewers.

---

### ADR-02: Strict Data Contracts via Pydantic v2
* **Context**: Information passed between the Preprocessor, Intent Classifier, Knowledge Retriever, Response Generator, and Automation Gatekeeper must maintain deterministic structure and type safety.
* **Decision**: All entities and pipeline payloads are defined as strict **Pydantic v2** models with runtime validation and bounded ranges (e.g., `confidence: float = Field(ge=0.0, le=1.0)`).
* **Rationale**:
  1. Guarantees schema adherence across all internal stages and API inputs.
  2. Enables native FastAPI OpenAPI (Swagger) schema generation without duplicate code.
  3. Enforces strict parsing of LLM structured JSON output.

---

### ADR-03: Dual-Mode Architecture (LLM with High-Precision Deterministic Fallback)
* **Context**: In production systems, external LLM APIs may experience network timeouts, quota exhaustion, or rate limiting. Furthermore, take-home reviewers may evaluate the repository without entering private API keys.
* **Decision**: Implemented a dual-engine architecture:
  - *Engine A (Cloud LLM)*: Google Gemini API (`gemini-2.5-flash`) utilizing native JSON schema mode when `GEMINI_API_KEY` is provided.
  - *Engine B (Deterministic Semantic Engine)*: Hybrid k-NN exemplar matching powered by ChromaDB vector similarity, contextual lexicons, and regex entity extractors.
* **Rationale**:
  - Guarantees 100% test reliability and instant local evaluation out of the box without requiring API billing or keys.
  - Zero-drop graceful degradation: If the external API fails or is unconfigured, the system automatically falls back to Engine B without crashing.

---

### ADR-04: Conservative Risk Gatekeeper for Autonomous Actions
* **Context**: Customer service automation involves an inherent trade-off between ticket deflection (automation) and risk mitigation (human escalation). False Automation on an angry or compromised customer can cause brand reputation damage, churn, or legal liabilities.
* **Decision**: The automation engine operates as a **conservative, high-precision risk gate**. When in doubt (low confidence, novel queries, severe distress, PII exposure), the system defaults to `ESCALATE_TO_HUMAN`.
* **Rationale**:
  - Operational cost of a human reviewing a routine ticket is low.
  - Operational and brand cost of an AI bot hallucinating or dismissing an angry customer in a public Twitter thread is catastrophic.
  - Target: **0% False Automation Rate on High-Risk Inquiries**.

---

## 2. Automation vs Escalation Decision Policy Matrix

The gatekeeper evaluates five distinct risk dimensions before authorizing an automated response:

```
[Inbound Tweet & Draft Response]
       │
  (1) Accidental PII Exposed? ───────► (Yes) ──► ESCALATE_TO_HUMAN (Privacy Specialist)
       │ (No)
  (2) Crisis, Legal Threat, Outrage? ► (Yes) ──► ESCALATE_TO_HUMAN (Executive Care / Safety)
       │ (No)
  (3) High-Risk Intent?
       ├── COMPLAINT_FEEDBACK ───────► (Yes) ──► ESCALATE_TO_HUMAN (Senior CX Supervisor)
       ├── ACCOUNT_SECURITY ─────────► (Yes) ──► ESCALATE_TO_HUMAN (Account Security Team)
       └── Urgent Billing Dispute ────► (Yes) ──► ESCALATE_TO_HUMAN (Billing Operations)
       │ (No)
  (4) Confidence >= 0.75 AND
      Grounding Similarity >= 0.45? ──► (No)  ──► ESCALATE_TO_HUMAN (Tier 2 Review Queue)
       │ (Yes)
  (5) AUTOMATE (Tier 1 Automated Fast-Path)
```

### Detailed Decision Criteria

| Risk Dimension | Trigger Conditions | Routing Assignment | Action Taken |
| :--- | :--- | :--- | :--- |
| **PII Protection** | 16-digit card number, personal phone number, or email detected in public tweet. | `Privacy & Data Protection Specialist` | Public text is sanitized; customer is routed to secure private DM channel for verification. |
| **Legal / Brand Crisis** | Threatening attorney/lawsuit, regulatory filing (FTC/DOT), public safety violation, severe outrage. | `Senior Customer Experience Supervisor` / `Crisis Team` | Auto-reply halted; immediate priority routing to specialized supervisor. |
| **Account Compromise** | Locked Apple ID/account, password reset failure, unauthorized 2FA SMS code. | `Account Security & Fraud Prevention` | Account security overrides cannot be automated publicly; manual identity verification initiated. |
| **Financial Dispute** | Disputed ride fares, unexpected charges, recurring auto-renewals with negative sentiment. | `Billing & Financial Operations` | Disputed transactions require authorized human agent override in payment gateway. |
| **Informational Inquiries** | General FAQ, return policy windows, luggage limits, self-serve invoice downloads with neutral sentiment. | `Tier 1 Automated Fast-Path` | Auto-response dispatched instantly ($\le 280$ characters) grounded in historical brand precedents. |

---

## 3. Decision Audit Log Schema (`logs/decision_audit.jsonl`)

Every triage transaction is persisted to an append-only JSONL log file with the following structured schema:

```json
{
  "record_id": "4b7b3791-c97b-4029-a1d2-06b64d1f27fa",
  "timestamp": "2026-09-11T16:45:22.184912+00:00",
  "inbound_tweet": "@AmazonHelp My package #402-8921821 is delayed and tracking is stuck!",
  "cleaned_tweet": "@AmazonHelp My package #402-8921821 is delayed and tracking is stuck!",
  "contains_masked_pii": false,
  "intent": "ORDER_DELIVERY_ISSUE",
  "intent_confidence": 0.85,
  "sentiment": "NEGATIVE",
  "urgency": "MEDIUM",
  "retrieved_exemplars_count": 3,
  "top_exemplar_similarity": 0.8505,
  "generated_reply": "We're sorry for the delay with your delivery! Please send us a DM with your order number and full delivery address so we can check the carrier status immediately: amzn.to/dm",
  "dm_suggested": true,
  "decision": "AUTOMATE",
  "decision_confidence": 0.85,
  "routing_team": "Tier 1 Automated Fast-Path",
  "decision_reasoning": "Safe for instant automation. High intent confidence (0.85) with strong historical grounding precedent (similarity: 0.85). Customer sentiment is NEGATIVE with no detected security, PII, or high-risk escalation flags.",
  "risk_factors": [],
  "execution_time_ms": 342.1
}
```

### Field Definitions

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `record_id` | `UUIDv4` | Unique identifier for the triage transaction. |
| `timestamp` | `ISO-8601 UTC` | Exact execution timestamp for compliance audit trails. |
| `inbound_tweet` | `string` | Raw customer tweet as received. |
| `cleaned_tweet` | `string` | Normalized tweet text with PII masked. |
| `contains_masked_pii` | `boolean` | Flag indicating whether personal identifiable information was detected. |
| `intent` | `string` | Primary predicted intent from 6-intent taxonomy. |
| `intent_confidence` | `float` | Model confidence score ($0.0 - 1.0$). |
| `sentiment` | `string` | Sentiment classification (`POSITIVE`, `NEUTRAL`, `NEGATIVE`, `SEVERELY_DISSATISFIED`). |
| `urgency` | `string` | Urgency classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`). |
| `retrieved_exemplars_count` | `int` | Number of historical brand exemplars retrieved via RAG. |
| `top_exemplar_similarity` | `float` | Cosine similarity score of the top historical match ($0.0 - 1.0$). |
| `generated_reply` | `string` | Bounded draft reply ($\le 280$ characters). |
| `dm_suggested` | `boolean` | Indicates whether response directs customer to private DM. |
| `decision` | `string` | Triage decision: `AUTOMATE` or `ESCALATE_TO_HUMAN`. |
| `decision_confidence` | `float` | Safety rating of the triage decision ($0.0 - 1.0$). |
| `routing_team` | `string` | Assigned human department or automated queue. |
| `decision_reasoning` | `string` | Natural language explanation justifying the triage outcome. |
| `risk_factors` | `list[string]` | Specific safety or risk triggers detected during evaluation. |
| `execution_time_ms` | `float` | End-to-end pipeline latency in milliseconds. |

---

## 4. Production Case Studies & Audit Samples

### Case Study 1: Routine Informational Query (Safe Automation)
* **Customer Tweet**: `@NikeSupport What is your holiday return policy for shoes purchased in November? Can they be returned in January?`
* **Intent**: `POLICY_GENERAL_FAQ` (Confidence: 0.94)
* **Top Exemplar**: `@NikeSupport ... Nike members enjoy a 60-day return policy ...` (Similarity: 0.92)
* **Decision**: `AUTOMATE`
* **Routing Team**: `Tier 1 Automated Fast-Path`
* **Audit Reasoning**: *"Safe for instant automation. High intent confidence (0.94) with strong historical grounding precedent (similarity: 0.92). Customer sentiment is NEUTRAL with no detected security, PII, or high-risk escalation flags."*

### Case Study 2: Accidental Public PII Exposure (Privacy Escalation)
* **Customer Tweet**: `@AmazonHelp Refund my card 4532 9901 2281 9921 right now or I cancel Prime!`
* **Sanitized Text**: `@AmazonHelp Refund my card [MASKED_CARD_NUMBER] right now or I cancel Prime!`
* **Intent**: `BILLING_REFUND_INQUIRY` (Confidence: 0.88)
* **Risk Factors**: `["Customer publicly shared sensitive PII (card, phone, or email).", "Disputed charge or urgent refund inquiry."]`
* **Decision**: `ESCALATE_TO_HUMAN`
* **Routing Team**: `Privacy & Data Protection Specialist`
* **Audit Reasoning**: *"Escalated to human agent: Sensitive PII detected in public tweet; requires secure manual DM handling. Financial transactions and disputed charges require authorized billing agent review."*

### Case Study 3: Legal Threat & Medical Crisis (Executive Escalation)
* **Customer Tweet**: `@British_Airways You lost our medication luggage 5 days ago! We are contacting our attorney to sue!`
* **Intent**: `COMPLAINT_FEEDBACK_ESCALATION` (Confidence: 0.96)
* **Sentiment / Urgency**: `SEVERELY_DISSATISFIED` / `CRITICAL`
* **Decision**: `ESCALATE_TO_HUMAN`
* **Routing Team**: `Senior Customer Experience Supervisor`
* **Audit Reasoning**: *"Escalated to human agent: Customer is severely dissatisfied or in critical distress; automated reply poses PR and churn risk. Direct complaints and legal/service escalations require empathetic human de-escalation."*

### Case Study 4: Account Security & Lockout (Fraud Escalation)
* **Customer Tweet**: `@AppleSupport My Apple ID was locked for security reasons and I lost my trusted phone number!`
* **Intent**: `ACCOUNT_SECURITY_ACCESS` (Confidence: 0.95)
* **Decision**: `ESCALATE_TO_HUMAN`
* **Routing Team**: `Account Security & Fraud Prevention`
* **Audit Reasoning**: *"Escalated to human agent: Account security actions require manual verification to prevent account takeover."*
