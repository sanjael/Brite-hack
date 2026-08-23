# Calder County — Automated Casework Assistant (Morning Referral Run)

**Brite Spark 2026 Hackathon Submission — Agentic AI / Guardrails**  
**Problem Statement:** The Caseworker's Morning  
**Policy Reference:** ACA-2026/1 & ACA-2026/2 Amendment  

---

## Project Overview

Every morning, caseworkers at the Calder County Department of Household Services process overnight referrals, cross-reference resident histories, draft triage notes, and determine appropriate actions.

This submission implements a **lean, policy-governed Agentic AI system** built with **LangGraph**, **Groq LLM**, and a **hard security execution boundary**.

### Core Value Proposition: Deterministic Security Boundary & Policy Handoffs
> *The reasoning model can analyze referrals and propose actions for safe cases, but it is **structurally prohibited** from drafting triage notes for households containing minors (ACA-2026/2 Section 3.9) and **structurally incapable** of executing protected side-effects without deterministic policy authorization and valid human supervisor approval.*

---

## Architecture Diagram

```text
                     START
                       │
                       ▼
                 LOAD QUEUE
                       │
                       ▼
               SELECT REFERRAL
                       │
                 More referrals?
                  /           \
                NO             YES
                ↓               ↓
               END        FETCH HISTORY
                                │
                         History available?
                          /            \
                        NO              YES
                        ↓                ↓
                 NEXT REFERRAL    HOUSEHOLD POLICY
                                      │
                            ┌─────────┴─────────┐
                            ↓                   ↓
                       HANDOFF             SAFE
                            ↓                   ↓
                     CREATE HANDOFF       AI TRIAGE
                            ↓                   ↓
                     NEXT REFERRAL       POLICY CHECK
                                             │
                              ┌──────────────┼──────────────┐
                              ↓              ↓              ↓
                           ALLOWED       APPROVAL        BLOCK/OTHER
                              │           REQUIRED            │
                              ↓              ↓                ↓
                           EXECUTE      HUMAN APPROVAL      ESCALATE
                                             │
                                      ┌──────┴──────┐
                                      ↓             ↓
                                   APPROVED      REJECTED
                                      ↓             ↓
                                   EXECUTE       ESCALATE
                                      │             │
                                      └──────┬──────┘
                                             ↓
                                      NEXT REFERRAL
                                             │
                                             └──────→ SELECT
```

---

## Directory Structure

```text
caseworker-morning/
│
├── README.md                   # Project overview & running instructions
├── DECISIONS.md                # Key architecture decisions
├── AI-USAGE.md                 # AI disclosure report
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
│
├── authority-policy.md         # Policy ACA-2026/1 & ACA-2026/2 Amendment
├── referral-queue.json         # 12 overnight referrals (Source of truth)
│
├── services/
│   ├── history_service.py      # Resident History API HTTP server
│   └── _history_data.json      # Resident history database
│
├── app/
│   ├── main.py                 # CLI main entrypoint (python -m app.main)
│   ├── graph.py                # LangGraph StateGraph & security nodes
│   ├── policy.py               # Deterministic Policy Engine (ACA-2026/1 & /2)
│   ├── history.py              # Resident History API client
│   ├── agent.py                # Groq LLM reasoning & triage generator
│   └── models.py               # Pydantic data schemas
│
├── tests/
│   ├── test_policy.py          # Policy engine unit tests
│   ├── test_guardrail.py       # Hard execution boundary tests
│   ├── test_run.py             # Full 12-referral queue test
│   └── test_aca_2026_2.py      # ACA-2026/2 minor household & handoff tests
│
└── artifacts/
    ├── runs/                   # Structured run execution JSON traces
    ├── escalations/            # Markdown & JSON escalation reports
    └── handoffs/               # ACA-2026/2 caseworker handoff artifacts
```

---

## Setup & Quickstart

### 1. Prerequisites
* Python 3.11+

### 2. Environment Setup
Clone repository and copy `.env.example`:
```bash
cp .env.example .env
```

Set your Groq API key in `.env`:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
HISTORY_API_URL=http://127.0.0.1:8083
```
*(Note: If `GROQ_API_KEY` is omitted, the application uses an internal analytical fallback for offline testing).*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Running the System

### Step 1: Start Resident History API
In terminal 1:
```bash
python3 services/history_service.py --port 8083
```
*(PowerShell: `python services/history_service.py --port 8083`)*

### Step 2: Run Agent Workflow

#### Interactive CLI Mode (Human Approval Prompt)
```bash
python -m app.main
```

#### Automated Demo Mode (Non-interactive auto-approval)
```bash
python -m app.main --demo
```

#### Streamlit Web UI Mode
In terminal 2:
```bash
streamlit run frontend/app.py
```
*(Launches an interactive web dashboard at http://localhost:8501 for visual queue processing, interactive human gate, and live audit analytics).*

When a referral requires supervisor approval (e.g. `RF-2026-0423` updating payment details), the system pauses, displays full context, asserts `NO ACTION HAS BEEN EXECUTED`, and prompts:
```text
Approve? [y/N]:
```

---

## Running Tests

Run the full test suite (including Day 1 tests and Day 2 ACA-2026/2 tests):
```bash
pytest -v
```

---

## Summary of 12-Referral Queue Processing

* **Caseworker Handoff Required (ACA-2026/2 Section 3.9 — Minor in Household)**:
  * `RF-2026-0412`: Household contains 5-year-old child William Iverson $\rightarrow$ Triage drafting restricted $\rightarrow$ `HANDOFF_REQUIRED` artifact created at `artifacts/handoffs/RF-2026-0412.json` with zero triage note generated.
* **Allowed Autonomously (Section 2)**:
  * `RF-2026-0413`: Record change of address
  * `RF-2026-0416`: Review household composition
  * `RF-2026-0417`: Draft explanatory note
  * `RF-2026-0420`: Flag for contact attempt
  * `RF-2026-0421`: Review household composition
  * `RF-2026-0422`: Draft triage note for supervisor
* **Supervisor Approval Required (Section 3)**:
  * `RF-2026-0414`: Review award
  * `RF-2026-0418`: Review award
  * `RF-2026-0419`: Record income change
  * `RF-2026-0423`: Update payment details
* **Explicitly Denied & Escalated (Section 3/4)**:
  * `RF-2026-0415`: Suspend assistance pending investigation (Counter-Fraud allegation). Prohibited under Policy Sections 3.2 & 3.7; escalated under Section 4.1.

