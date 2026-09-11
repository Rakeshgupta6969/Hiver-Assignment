# Hiver AI Customer Support Agent (Twitter Intelligence Pipeline)

Production-grade AI customer support agent designed for **Twitter (X)** customer support conversations, built for the **Hiver SDE Intern take-home assignment**.

The system addresses three core customer service tasks:
1. **Intent Classification**: Identifying issue categories from a 6-intent mutually exclusive, collectively exhaustive (MECE) taxonomy.
2. **Response Generation**: Synthesizing helpful replies grounded in historical brand customer support interactions using Retrieval-Augmented Generation (RAG).
3. **Automation Decision**: Evaluating risk, sentiment, complexity, and confidence to decide between autonomous self-serve reply (`AUTOMATE`) vs human routing (`ESCALATE_TO_HUMAN`) with transparent, audit-ready reasoning.

---

## Architecture Overview

```
                               ┌─────────────────────────────────────────┐
                               │   Interactive Web Dashboard / Client    │
                               │  (Live pipeline inspection & presets)   │
                               └────────────────────┬────────────────────┘
                                                    │ HTTP / JSON
                               ┌────────────────────▼────────────────────┐
                               │          FastAPI Service Layer          │
                               │    (/api/process, /api/batch, /health)  │
                               └────────────────────┬────────────────────┘
                                                    │
┌───────────────────────────────────────────────────▼───────────────────────────────────────────────────┐
│                                       Modular AI Pipeline Engine                                      │
│                                                                                                       │
│   [1. Preprocessing & Sanitization]                                                                   │
│        • Strips Twitter noise, extracts handles, masks accidental PII (cards, emails, phones)         │
│        ▼                                                                                              │
│   [2. Intent Classification & Sentiment Engine]                                                       │
│        • Predicts intent category, confidence, sentiment (4 levels), and urgency (4 levels)           │
│        ▼                                                                                              │
│   [3. Semantic Knowledge Retriever (ChromaDB RAG)]                                                    │
│        • Vector search over historical customer-brand resolution pairs filtered by intent             │
│        ▼                                                                                              │
│   [4. Grounded Response Generator]                                                                    │
│        • Drafts reply grounded strictly in historical brand precedents within Twitter 280-char limit  │
│        ▼                                                                                              │
│   [5. Automation & Escalation Gatekeeper]                                                             │
│        • Multi-factor risk evaluation: AUTOMATE vs ESCALATE_TO_HUMAN with transparent audit reasoning │
└───────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                    │
                               ┌────────────────────▼────────────────────┐
                               │      Data & Knowledge Base Layer        │
                               │  • Twitter Support Inbound-Brand Pairs  │
                               │  • Local In-Process ChromaDB Store      │
                               └─────────────────────────────────────────┘
```

---

## 1. Intent Taxonomy (Task 1)

Customer support on Twitter requires a focused, actionable taxonomy rather than generic categories:

| Intent Category | Scope & Customer Need | Action / Resolution Pathway |
| :--- | :--- | :--- |
| `ORDER_DELIVERY_ISSUE` | Shipping delays, lost/damaged packages, delivery address updates, tracking links. | Provide self-serve tracking link or request order ID via DM. |
| `BILLING_REFUND_INQUIRY` | Unexpected/duplicate charges, payment failures, refund timelines, invoices. | Direct to billing history or escalate to financial operations via DM. |
| `TECHNICAL_PRODUCT_SUPPORT` | App crashes, checkout errors, login/authentication bugs, OS compatibility. | Provide troubleshooting SOP (cache, reboot, clean reinstall) or bug triage. |
| `ACCOUNT_SECURITY_ACCESS` | Account lockouts, password resets, 2FA errors, compromised accounts. | High-priority security triage; guide to official identity recovery portal. |
| `POLICY_GENERAL_FAQ` | Return/exchange windows, warranty coverage, baggage limits, business hours. | Instant self-serve answer with official help documentation citations. |
| `COMPLAINT_FEEDBACK_ESCALATION` | Severe dissatisfaction, employee misconduct, legal/media threats, churn risk. | Immediate de-escalation; route directly to Senior CX Supervisor. |

---

## 2. Response Generation Grounded in Historical Brand Responses (Task 2)

A common failure mode in customer support bots is hallucination (promising unauthorized refunds, inventing non-existent features, or robotic dismissals).

- **Grounding Mechanism**: The system indexes historical Twitter support conversations across major customer service accounts (`AmazonHelp`, `AppleSupport`, `Uber_Support`, `Delta`, `SpotifyCares`, `NikeSupport`).
- **Semantic Retrieval**: For every inbound tweet, ChromaDB retrieves top-$K$ ($K=3$) semantically matching resolution exemplars matching the classified intent.
- **Constraints Enforced**:
  - Max 280 characters (hard Twitter boundary).
  - Emulates brand tone (empathetic, professional, solution-oriented).
  - Explicit Direct Message (DM) redirect when private account verification is required.

---

## 3. Automation Decision & Escalation Gatekeeper (Task 3)

The automation gatekeeper operates as a **conservative, high-precision risk filter**:

```
                         [Inbound Tweet & Draft Response]
                                        │
                      Critical Distress or Legal Threat?
                                     /     \
                                  (Yes)    (No)
                                   /         \
                      ESCALATE_TO_HUMAN    Intent is Account Security / Dispute?
                                                  /     \
                                               (Yes)    (No)
                                                /         \
                                   ESCALATE_TO_HUMAN    Confidence >= 0.75 & Similarity >= 0.45?
                                                               /     \
                                                            (Yes)    (No)
                                                             /         \
                                                         AUTOMATE    ESCALATE_TO_HUMAN
```

### Transparent Decision Schema:
```json
{
  "decision": "AUTOMATE",
  "confidence": 0.95,
  "routing_team": "Tier 1 Automated Fast-Path",
  "reasoning": "Safe for instant automation. High intent confidence (0.96) with strong historical grounding precedent (similarity: 0.77). Customer sentiment is NEUTRAL with no detected security, PII, or high-risk escalation flags.",
  "urgency": "LOW",
  "risk_factors": []
}
```

---

## Project Structure

```
.
├── api/
│   └── main.py                     # FastAPI server (/api/process, /api/batch, /api/logs)
├── data/
│   ├── twitter_support_conversations.json # Representative customer-brand dataset
│   ├── golden_evaluation_set.json  # 30-case annotated golden benchmark dataset
│   └── chroma_db/                  # Persistent local ChromaDB vector store
├── logs/
│   └── decision_audit.jsonl        # Append-only structured decision audit log
├── src/
│   ├── config.py                   # App configuration & environment variables
│   ├── models.py                   # Strict Pydantic models & MECE taxonomy enums
│   ├── preprocessor.py             # Twitter text cleaning & PII masking
│   ├── intent_classifier.py        # Intent classification engine (LLM + local fallback)
│   ├── knowledge_retriever.py      # ChromaDB vector retrieval of historical exemplars
│   ├── response_generator.py       # Grounded response generator
│   ├── automation_gatekeeper.py    # Multi-factor escalation decision engine
│   ├── decision_logger.py          # Structured audit logging engine
│   └── pipeline.py                 # End-to-end SupportAgent pipeline orchestrator
├── static/
│   ├── index.html                  # Interactive Dashboard UI
│   ├── style.css                   # Modern dark-mode glassmorphic styling
│   └── app.js                      # Live pipeline visualization & presets
├── tests/
│   ├── test_api.py                 # FastAPI endpoint integration tests
│   ├── test_automation_gatekeeper.py # Gatekeeper & safety tests
│   ├── test_generator.py           # Grounding & Twitter length tests
│   ├── test_intent_classifier.py   # Intent classification unit tests
│   ├── test_preprocessor.py        # PII masking & normalization tests
│   └── test_retriever.py           # ChromaDB retrieval tests
├── evaluate.py                     # 30-case golden benchmark & report generator
├── EVALUATION_REPORT.md            # Formal evaluation report with confusion matrix
├── run.py                          # Server launcher
├── requirements.txt                # Python package dependencies
└── README.md
```

---

## Deliverables Summary for Hiver Assignment

| Deliverable | Location | Description |
| :--- | :--- | :--- |
| **Golden Evaluation Set** | [`data/golden_evaluation_set.json`](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/data/golden_evaluation_set.json) | 30 diverse real-world customer tweets with ground-truth intents, expected decisions, routing teams, and rationale. |
| **Decision Audit Log** | [`logs/decision_audit.jsonl`](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/logs/decision_audit.jsonl) | Append-only audit trail logging every triage decision, confidence score, and rationale. Accessible via `GET /api/logs`. |
| **Formal Evaluation Report** | [`EVALUATION_REPORT.md`](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/EVALUATION_REPORT.md) | Comprehensive quantitative evaluation with per-intent Precision/Recall/F1, confusion matrix, and safety metrics. |
| **Complete Source & Tests** | [`src/`](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/src/), [`tests/`](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/tests/) | Full modular pipeline with 25 passing automated unit & integration tests. |

---

## Getting Started

### 1. Setup Virtual Environment
```bash
# Clone or navigate to the workspace
cd Hiver

# Create and activate virtual environment
py -m venv venv
.\venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key. When omitted, system automatically uses the local deterministic semantic engine. |
| `GOOGLE_API_KEY` | *(empty)* | Alternative alias for Google Gemini API key. |
| `GEMINI_MODEL_NAME` | `gemini-2.5-flash` | Gemini model variant used for generation and classification. |
| `FORCE_LOCAL_FALLBACK` | `false` | When set to `true`, forces local deterministic semantic mode even if an API key is present. |

### 4. Run Automated Test Suite
```bash
pytest -v
```
*Expected: 25 passing tests covering all components.*

### 5. Run Golden Benchmark Evaluation
```bash
python evaluate.py
```
*Evaluates the 50-case golden test set, outputs metrics, and generates `EVALUATION_REPORT.md`.*

### 6. Launch Interactive Web Dashboard
```bash
python run.py
```
Open **http://127.0.0.1:8000** in your browser.
Interactive features:
- Test preset chips (Delayed Package, Duplicate Charge, App Crash, Account Compromised, FAQ, Legal Escalation, Public PII Leak).
- Step-by-step visual breakdown of the 3 tasks.
- Grounding precedent accordion showing historical brand resolution matches.
- OpenAPI Swagger documentation at **http://127.0.0.1:8000/docs**.
- Audit log endpoint at **http://127.0.0.1:8000/api/logs**.

---

## Dataset Information & Scaling to Full Twitter Support Data

### Demo Seed Subset vs Full Kaggle Dataset
- **The Challenge**: The complete Kaggle *Customer Support on Twitter* (`twcs.csv`) dataset contains **~2.81 million tweets (~700 MB)**. Ingesting, embedding, and committing 3 million interactions into a Git repository is impractical (exceeds GitHub file limits) and requires hours of GPU compute.
- **Selection of 28-Pair Seed Subset**: We selected 28 authentic first-turn customer queries paired with official brand first-response resolutions across 7 premier customer support handles (`@AmazonHelp`, `@AppleSupport`, `@Uber_Support`, `@Delta`, `@SpotifyCares`, `@NikeSupport`, `@HiverSupport`).
- **Why It Is Sufficient**: Provides dense, balanced semantic coverage across all 6 intents and major customer support verticals (e-commerce, hardware, fintech/ride-hailing, travel, media streaming, and B2B SaaS).
- **Scaling with `ingest_twcs_csv.py`**:
  If you have the full Kaggle `twcs.csv` file, ingest any arbitrary number of conversation pairs into ChromaDB using the included CLI tool:
  ```bash
  python data/ingest_twcs_csv.py --csv /path/to/twcs.csv --max-pairs 5000
  ```

---

## Golden Benchmark Results

```
=====================================================================================
 HIVER AI CUSTOMER SUPPORT AGENT - GOLDEN BENCHMARK EVALUATION
=====================================================================================
• Total Golden Test Cases:           50
• Overall Intent Accuracy:           88.0% (44/50)
• Overall Automation Gate Accuracy:  94.0% (47/50)
• High-Risk False Automations:       0 (0.0%) [TARGET: 0 - 100% Safety Compliance]
• Average End-to-End Latency:        537.36 ms
• P50 / P95 Latency:                 525.91 ms / 642.62 ms
=====================================================================================
```
Full quantitative breakdown, confusion matrix, and safety analysis are available in [EVALUATION_REPORT.md](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/EVALUATION_REPORT.md).

---

## System Limitations

1. **Single-Turn Triage**: Currently focuses on the crucial first turn of an inbound customer tweet. Multi-turn dialogue thread reconciliation is handled through DM redirects rather than persistent thread states.
2. **Public Twitter Constraints**: To adhere to strict consumer privacy laws, public replies cannot execute account-level actions (e.g., executing a refund directly in a tweet). The system safely routes customers to secure DMs.
3. **Language Scope**: Currently optimized for English customer support interactions.

---

## Future Improvements

1. **Multi-Turn Thread Context**: Ingesting Twitter conversation tree hierarchies to maintain context across multi-turn exchanges.
2. **Direct CRM Integration**: Integrating directly into Hiver's shared mailbox and ticket routing APIs to automatically create tagged tickets in Gmail.
3. **Active Learning from Agent Edits**: Continuously re-indexing human agent edits to improve retrieval grounding over time.
4. **Multi-Lingual Embeddings**: Upgrading to multilingual vector models (e.g., `paraphrase-multilingual-MiniLM-L12-v2`) for global cross-language support.


