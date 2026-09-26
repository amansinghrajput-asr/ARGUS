# ARGUS — Backend 1

**Developer:** Aman Singh  
**Role:** Backend Developer 1  
**GitHub Branch:** `amanSR/backend-1`  
**Workspace Directory:** `AmanSR_backend_1/`

---

## 📌 Project Overview

**ARGUS** is an AI-powered customer support intelligence system designed to triage messy multi-part complaints, coordinate specialist investigative agents, maintain persistent conversation memory, and provide zero-repeat human handoffs.

This directory (`AmanSR_backend_1/`) is the isolated workspace dedicated exclusively to **Backend Developer 1**.

---

## 🎯 Confirmed Backend 1 Scope

1. **Customer Data & APIs:** Customer profiles, contact lookups, account status, and tier info.
2. **Order Data & APIs:** Contextual order records, line items, delivery and payment statuses.
3. **Complaint & Case Lifecycle:** Ingestion of raw complaints, issue triage, confidence-gated status tracking (`open` -> `investigating` -> `resolved_ai` / `escalated_to_human` -> `closed`).
4. **Conversation History & Zero-Repeat Escalation:** Message turns, specialist investigation trails, and the structured handoff packet for human agents.
5. **Knowledge Base / FAQ Data:** Canonical support articles and policies referenced during investigation.
6. **Orchestrator Context Hydration:** Single endpoint (`/api/v1/context/hydrate`) supplying combined context to the n8n orchestrator.

---

## 📁 Scaffolding Architecture

```text
AmanSR_backend_1/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cases.py        # Case lifecycle endpoints
│   │   │   │   ├── context.py      # n8n context hydration endpoint
│   │   │   │   ├── customers.py    # Customer profile endpoints
│   │   │   │   ├── history.py      # Conversation turns & handoff packet
│   │   │   │   ├── knowledge.py    # FAQ article endpoints
│   │   │   │   └── orders.py       # Order endpoints
│   │   │   ├── __init__.py
│   │   │   └── router.py           # V1 route aggregator
│   │   ├── __init__.py
│   │   └── router.py               # Top-level API router
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Environment configuration settings
│   │   └── database.py             # Async MongoDB connection lifecycle
│   ├── models/
│   │   ├── __init__.py
│   │   ├── case.py                 # ComplaintCase schema
│   │   ├── customer.py             # Customer schema
│   │   ├── history.py              # ConversationHistory & Turn schemas
│   │   ├── knowledge.py            # FAQArticle schema
│   │   └── order.py                # Order schema
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── case_repo.py            # Cases collection repository
│   │   ├── customer_repo.py        # Customers collection repository
│   │   ├── history_repo.py         # Conversation histories repository
│   │   ├── knowledge_repo.py       # FAQ articles repository
│   │   └── order_repo.py           # Orders collection repository
│   ├── services/
│   │   ├── __init__.py
│   │   ├── case_service.py         # Case lifecycle business logic
│   │   ├── context_service.py      # n8n context hydration logic
│   │   └── handoff_service.py      # Zero-repeat handoff packet builder
│   ├── __init__.py
│   └── main.py                     # FastAPI application entry point
├── data/
│   ├── seed_customers.json         # Demo customer fixture
│   ├── seed_faq.json               # Demo FAQ fixture
│   └── seed_orders.json            # Demo orders fixture
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest fixtures
│   └── test_scaffolding.py         # Structural verification tests
├── .env.example                    # Environment variable template
├── requirements.txt                # Python dependencies
└── README.md                       # This documentation
```

---

## 🚀 Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
```

### 3. Run Development Server
```bash
uvicorn app.main:app --reload --port 8000
```
Interactive API docs will be available at: `http://localhost:8000/docs`

---

## 🔒 Directory Guidelines

- **Isolation:** All Backend 1 code, models, tests, and configurations reside inside `AmanSR_backend_1/`.
- **Integrity:** Never modify other developers' files or the root project assignment files.
- **Git Branch:** Work remains committed to `amanSR/backend-1`.
