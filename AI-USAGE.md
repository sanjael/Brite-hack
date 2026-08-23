# AI Usage Disclosure (AI-USAGE.md)

**Project:** Brite Spark 2026 — Agentic AI / Guardrails  
**Problem Statement:** The Caseworker's Morning  

---

## 1. Overview
In accordance with the Brite Spark 2026 Participant Handbook, this document details the AI tools and models utilized during the architecture, development, testing, and documentation of this project submission.

---

## 2. AI Tools & Models Used

| AI Tool / Model | Purpose / Phase | Scope of Assistance |
|:---|:---|:---|
| **Google Gemini 3.6 Flash / Antigravity IDE** | Planning & Implementation Lead | Scaffolded project structure, generated LangGraph state graph code, policy engine, security unit tests, and documentation. |
| **Groq API (Llama 3.3 70B Versatile)** | Runtime LLM Reasoning Engine | Performs referral summarization, historical event extraction, and triage note drafting during agent execution. |

---

## 3. Human Engineering & Verification
All AI-assisted outputs were rigorously verified and validated by the implementation team:
* **Security & Authorization Verification**: Ensured that LLM prompts do not act as the authority boundary, and verified that `ControlledExecutor` enforces token-based authorization independently of LLM outputs.
* **Policy Compliance Audit**: Verified that rules in `config/policy.json` strictly match Calder County Policy **ACA-2026/1** from `authority-policy.md`.
* **Automated Test Validation**: Executed unit and integration tests (`pytest`) covering policy evaluation, guardrail enforcement, API client communication, and full queue processing.

---

## 4. Limitations & Safe Fallbacks
* The Groq LLM reasoning module is isolated from side-effect execution.
* An analytical fallback engine (`_fallback_analysis`) is included to ensure the system remains testable and runnable even when an external LLM API key is absent.
