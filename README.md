# Hiver AI Customer Support Agent (Twitter Intelligence Pipeline)

An enterprise-grade, production-ready AI customer support agent designed for **Twitter (X)** customer support conversations, built for the **Hiver SDE Intern take-home assignment**.

---

## 1. Project Overview

Customer support on Twitter presents unique technical and operational challenges:
- **Character Constraints & Signal-to-Noise**: Inbound tweets are under 280 characters, filled with typos, slang, handles, and fragmented context.
- **Public Visibility & High Brand Stakes**: Every response is public; an AI hallucination or a robotic response to an angry user can trigger brand backlash.
- **Privacy & PII Protection**: Public tweets must never expose sensitive customer data (card numbers, passwords, phone numbers). Customers must be redirected to secure Direct Messages (DMs).
- **The Core Automation Trade-off**:
  - *False Automation (Bot replies when human was needed)*: Drives customer churn, safety risks, and PR crises.
  - *False Escalation (Escalates when bot was safe)*: Inflates human ticket volume and eliminates automation ROI.

To solve this, the Hiver AI Customer Support Agent implements three core tasks:
1. **Intent Classification**: Classifies customer queries into a 6-intent mutually exclusive, collectively exhaustive (MECE) taxonomy with confidence scores, sentiment levels, and urgency ratings.
2. **Response Generation**: Generates brand-aligned replies strictly grounded in historical brand customer interactions via Retrieval-Augmented Generation (RAG) in ChromaDB, adhering to Twitter's 280-character limit.
3. **Automation Decision**: A multi-factor risk gatekeeper that evaluates whether to resolve automatically (`AUTOMATE`) or route to a specialized human team (`ESCALATE_TO_HUMAN`) with transparent, audit-ready reasoning.

---

## 2. Architecture Diagram

```
                               ┌─────────────────────────────────────────┐
                               │       Interactive Web Dashboard         │
                               │   (Live pipeline trace & test presets)  │
                               └────────────────────┬────────────────────┘
                                                    │ HTTP / JSON
                               ┌────────────────────▼────────────────────┐
                               │          FastAPI Service Layer          │
                               │  (/api/process, /api/batch, /api/logs)  │
                               └────────────────────┬────────────────────┘
                                                    │
┌───────────────────────────────────────────────────▼───────────────────────────────────────────────────┐
│                                       Modular AI Pipeline Engine                                      │
│                                                                                                       │
│   [1. Ingestion & Preprocessing]                                                                      │
│        • Strips Twitter noise, extracts @handles, masks accidental PII (cards, emails, phones)        │
│        ▼                                                                                              │
│   [2. Intent Classification & Sentiment Engine]                                                       │
│        • Dual-mode classifier: LLM structured output + hybrid vector k-NN semantic classifier         │
│        • Outputs: primary intent, confidence, sentiment (4 tiers), urgency (4 tiers), entities        │
│        ▼                                                                                              │
│   [3. Semantic Knowledge Retriever (ChromaDB RAG)]                                                    │
│        • Queries local ChromaDB vector store with ONNX all-MiniLM-L6-v2 embeddings                    │
│        • Fetches top-K historical brand resolution pairs filtered by predicted intent                 │
│        ▼                                                                                              │
│   [4. Grounded Response Generator]                                                                    │
│        • Synthesizes helpful reply strictly grounded in historical brand SOPs                         │
│        • Enforces Twitter 280-char limit and suggests DM redirect for account verification            │
│        ▼                                                                                              │
│   [5. Automation & Escalation Gatekeeper]                                                             │
│        • Multi-factor risk engine: checks PII, crisis sentiment, high-risk intents, and confidence    │
│        • Outputs: AUTOMATE vs ESCALATE_TO_HUMAN, safety score, assigned human team, and reasoning     │
│        ▼                                                                                              │
│   [6. Persistent Decision Audit Logger]                                                               │
│        • Appends complete transaction record to logs/decision_audit.jsonl                             │
└───────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                    │
                               ┌────────────────────▼────────────────────┐
                               │      Data & Knowledge Base Layer        │
                               │  • Twitter Support Inbound-Brand Pairs  │
                               │  • In-Process ChromaDB Vector Store     │
                               └─────────────────────────────────────────┘
```

---

## 3. Setup Instructions

### Prerequisites
- Python 3.10 to 3.13
- Git

### Step-by-Step Installation

1. **Clone or Navigate to the Workspace**:
   ```bash
   cd Hiver
   ```

2. **Create and Activate a Virtual Environment**:
   * Windows (PowerShell):
     ```powershell
     py -m venv venv
     .\venv\Scripts\activate
     ```
   * Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Dependencies include: `fastapi`, `uvicorn[standard]`, `pydantic`, `chromadb`, `google-genai`, `python-dotenv`, `httpx`, `pytest`.*

---

## 4. Environment Variables

The system operates in **dual mode**: it connects to a live Google Gemini LLM when an API key is provided, or seamlessly utilizes the local deterministic semantic engine (default) for zero-latency, offline execution.

Create a `.env` file in the project root (or copy `.env.example`):
```bash
cp .env.example .env
```

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key. When omitted, system automatically uses the local deterministic semantic engine. |
| `GOOGLE_API_KEY` | *(empty)* | Alternative alias for Google Gemini API key. |
| `GEMINI_MODEL_NAME` | `gemini-2.5-flash` | Gemini model variant used for LLM generation and classification. |
| `FORCE_LOCAL_FALLBACK` | `false` | When set to `true`, forces local deterministic semantic mode even if an API key is present. |

---

## 5. Dataset Preparation & Scaling

### Demo Seed Subset vs. Full Kaggle Dataset
- **The Challenge**: The canonical Kaggle *Customer Support on Twitter* (`twcs.csv`) dataset contains **~2.81 million tweets (~700 MB)**. Bundling a 700 MB CSV in a Git repository exceeds GitHub limits and requires hours of GPU compute to vectorize.
- **Demo Seed Subset (`data/twitter_support_conversations.json`)**:
  - Contains 28 representative customer-brand conversation pairs modeled directly on `twcs.csv`.
  - Balanced across 7 leading support accounts: `@AmazonHelp`, `@AppleSupport`, `@Uber_Support`, `@Delta`, `@SpotifyCares`, `@NikeSupport`, `@HiverSupport`.
  - Captures genuine resolution policies: carrier tracking portals (`amzn.to/dm`), Apple recovery portals (`iforgot.apple.com`), baggage emergency procedures, and clean reinstalls.
- **Why It Is Sufficient**:
  - Provides dense semantic coverage across all 6 intents.
  - ChromaDB indexes this in-process on startup in milliseconds with zero GPU/network dependencies.
- **Scaling to Full Kaggle Dataset (`data/ingest_twcs_csv.py`)**:
  To index arbitrary thousands or millions of interactions from Kaggle:
  ```bash
  python data/ingest_twcs_csv.py --csv /path/to/twcs.csv --max-pairs 5000
  ```

---

## 6. Running Instructions

### 1. Launch Interactive Web Dashboard & API Server
```powershell
python run.py
```
* Or directly via virtual environment executable:
```powershell
.\venv\Scripts\python.exe run.py
```
- Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser to interact with the dashboard.
- Open **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)** for interactive OpenAPI (Swagger) documentation.

### 2. Run the 50-Case Golden Benchmark Evaluation
```powershell
python evaluate.py
```
- Runs end-to-end evaluation against `data/golden_evaluation_set.json`.
- Outputs intent accuracy, gate accuracy, false automations, and latency metrics.
- Automatically generates [EVALUATION_REPORT.md](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/EVALUATION_REPORT.md).

### 3. Run Automated Unit & Integration Tests
```powershell
pytest -v
```
- Runs all 25 automated tests across 6 test modules covering preprocessing, classification, RAG retrieval, response generation, gatekeeper safety, and FastAPI REST endpoints.

---

## 7. API Documentation

The FastAPI backend exposes typed REST endpoints documented below:

### `POST /api/process`
Processes a single customer tweet through the full 5-stage pipeline.

**Request Body (`application/json`):**
```json
{
  "tweet_text": "@AmazonHelp My package was supposed to arrive yesterday! Where is order #402-8921821?",
  "brand_context": "AmazonHelp",
  "author_id": "customer_user"
}
```

**Response Body (`200 OK`):**
```json
{
  "inbound_tweet": "@AmazonHelp My package was supposed to arrive yesterday! Where is order #402-8921821?",
  "preprocessed": {
    "raw_text": "@AmazonHelp My package was supposed to arrive yesterday! Where is order #402-8921821?",
    "cleaned_text": "@AmazonHelp My package was supposed to arrive yesterday! Where is order #402-8921821?",
    "handles_detected": ["@AmazonHelp"],
    "contains_masked_pii": false,
    "original_length": 86,
    "cleaned_length": 86
  },
  "intent_classification": {
    "primary_intent": "ORDER_DELIVERY_ISSUE",
    "confidence": 0.85,
    "secondary_intent": null,
    "sentiment": "NEGATIVE",
    "urgency": "MEDIUM",
    "reasoning": "Classified as ORDER_DELIVERY_ISSUE based on contextual cues and matched support terms.",
    "extracted_entities": {
      "order_identifier": "402-8921821"
    }
  },
  "grounded_response": {
    "generated_reply": "We're sorry for the delay with your delivery! Please send us a DM with your order number and full delivery address so we can check the carrier status immediately: amzn.to/dm",
    "grounded_in_exemplars": [
      {
        "id": "TW_ORD_001",
        "brand": "AmazonHelp",
        "customer_query": "@AmazonHelp My package was supposed to arrive yesterday by 8 PM...",
        "brand_response": "We're sorry for the delay with your delivery! Please send us a DM...",
        "intent": "ORDER_DELIVERY_ISSUE",
        "similarity_score": 0.8505
      }
    ],
    "character_count": 173,
    "direct_message_suggested": true,
    "tone": "Grounded & Authoritative"
  },
  "automation_decision": {
    "decision": "AUTOMATE",
    "confidence": 0.85,
    "reasoning": "Safe for instant automation. High intent confidence (0.85) with strong historical grounding precedent (similarity: 0.85). Customer sentiment is NEGATIVE with no detected security, PII, or high-risk escalation flags.",
    "urgency": "MEDIUM",
    "routing_team": "Tier 1 Automated Fast-Path",
    "risk_factors": []
  },
  "execution_time_ms": 342.1
}
```

### `POST /api/batch`
Processes multiple tweets in a batch request.
- **Request**: List of `SupportAgentRequest` objects.
- **Response**: List of `SupportAgentResponse` objects.

### `GET /api/logs`
Returns the recent decision audit log records from `logs/decision_audit.jsonl`.
- **Query Parameters**: `limit` (default: 50).
- **Response**: Array of structured audit log objects.

### `GET /api/intents`
Returns the 6-intent taxonomy definitions and descriptions.

### `GET /api/health`
Returns system health, total indexed exemplars in ChromaDB, and active engine mode.

---

## 8. Evaluation Results

The agent was benchmarked on the **50-case Golden Evaluation Set** (`data/golden_evaluation_set.json`):

```
=====================================================================================
 HIVER AI CUSTOMER SUPPORT AGENT - GOLDEN BENCHMARK EVALUATION
=====================================================================================
• Total Golden Test Cases:           50
• Overall Intent Accuracy:           88.0% (44/50)
• Overall Automation Gate Accuracy:  94.0% (47/50)
• High-Risk False Automations:       0 (0.0%) [TARGET: 0 - 100% Safety Compliance]
• Mean End-to-End Latency:           537.36 ms
• P50 / P95 Latency:                 525.91 ms / 642.62 ms
=====================================================================================
```

### Per-Intent Performance Metrics

| Intent Category | Support | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: |
| `ORDER_DELIVERY_ISSUE` | 8 | 87.5% | 87.5% | **87.5%** |
| `BILLING_REFUND_INQUIRY` | 11 | 91.7% | 100.0% | **95.7%** |
| `TECHNICAL_PRODUCT_SUPPORT` | 10 | 100.0% | 80.0% | **88.9%** |
| `ACCOUNT_SECURITY_ACCESS` | 5 | 62.5% | 100.0% | **76.9%** |
| `POLICY_GENERAL_FAQ` | 8 | 85.7% | 75.0% | **80.0%** |
| `COMPLAINT_FEEDBACK_ESCALATION` | 8 | 100.0% | 87.5% | **93.3%** |

Full confusion matrix and case-by-case analysis are documented in [evaluation_report.md](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/evaluation_report.md).

---

## 9. System Limitations

1. **Single-Turn Triage**: Currently focuses on the crucial first turn of an inbound customer tweet. Multi-turn dialogue thread reconciliation is handled through DM redirects rather than persistent conversation states.
2. **Public Twitter Constraints**: To adhere to strict consumer privacy laws, public replies cannot execute account-level actions (e.g., executing a refund directly in a tweet). The system safely routes customers to secure DMs.
3. **Language Scope**: Currently optimized for English customer support interactions.

---

## 10. Future Improvements

1. **Multi-Turn Thread Context**: Ingesting Twitter conversation tree hierarchies to maintain context across multi-turn exchanges.
2. **Direct CRM Integration**: Integrating directly into Hiver's shared mailbox and ticket routing APIs to automatically create tagged tickets in Gmail.
3. **Active Learning from Agent Edits**: Continuously re-indexing human agent edits to improve retrieval grounding over time.
4. **Multi-Lingual Embeddings**: Upgrading to multilingual vector models (e.g., `paraphrase-multilingual-MiniLM-L12-v2`) for global cross-language support.

---

## Key Deliverables Summary

* **Project Overview & Architecture**: [README.md](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/README.md)
* **Architecture Decision Records & Triage Policies**: [decision_log.md](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/decision_log.md)
* **Formal Evaluation Report & Confusion Matrix**: [evaluation_report.md](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/evaluation_report.md)
* **50-Case Golden Evaluation Set**: [data/golden_evaluation_set.json](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/data/golden_evaluation_set.json)
* **Decision Audit Log (Append-only)**: [logs/decision_audit.jsonl](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/logs/decision_audit.jsonl)
* **Kaggle Dataset Scaling Tool**: [data/ingest_twcs_csv.py](file:///c:/Users/rg688/OneDrive/Desktop/Hiver/data/ingest_twcs_csv.py)
