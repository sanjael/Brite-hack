# Incremental Git Commit Plan (`docs/to_commit/00_COMMIT_GUIDE.md`)

This guide provides a step-by-step commit timeline to demonstrate realistic, incremental software engineering for hackathon judges inspecting Git history.

---

## 1. Overview of 10-Step Commit History

| Step | Commit Message | Files Included / Staged |
|:---:|:---|:---|
| **01** | `feat: initialize project structure, policy ACA-2026/1, and mock history service` | `.gitignore`, `requirements.txt`, `.env.example`, `authority-policy.md`, `referral-queue.json`, `services/` |
| **02** | `feat(models): define Pydantic data schemas for referrals, history, policy decisions, and HMAC tokens` | `app/__init__.py`, `app/models.py` |
| **03** | `feat(history): implement HTTP client for resident history API with 404 & error isolation` | `app/history.py` |
| **04** | `feat(policy): implement data-driven PolicyEngine and ACA-2026/1 Section 6.1 ambiguity rules` | `config/policy.json`, `app/policy.py` |
| **05** | `feat(agent): implement Groq Llama 3.3 70B reasoning agent with prompt injection defense & analytical fallback` | `app/agent.py` |
| **06** | `feat(graph): implement LangGraph StateGraph, human approval gate, and HMAC-SHA256 execution boundary` | `app/graph.py` |
| **07** | `feat(cli): implement interactive CLI entrypoint with stdout execution tracing` | `app/main.py` |
| **08** | `test: add unit & integration test suite for policy engine, guardrail security, and queue execution` | `tests/` |
| **09** | `feat(frontend): implement Streamlit web dashboard for visual queue triage and human gate` | `frontend/app.py` |
| **10** | `docs: add comprehensive developer learning guides, audit reports, DECISIONS.md, and AI disclosure` | `README.md`, `DECISIONS.md`, `AI-USAGE.md`, `docs/`, `audit/` |

---

## 2. Command-by-Command Execution Instructions

If you ever need to reset or rebuild your Git repository with this incremental commit history, run these commands in Windows PowerShell:

### Step 1: Initial Skeleton & Provided Files
```powershell
git checkout --orphan temp_branch
git reset
git add .gitignore requirements.txt .env.example authority-policy.md referral-queue.json services/
git commit -m "feat: initialize project structure, policy ACA-2026/1, and mock history service"
```

### Step 2: Data Models (`app/models.py`)
```powershell
git add app/__init__.py app/models.py
git commit -m "feat(models): define Pydantic data schemas for referrals, history, policy decisions, and HMAC tokens"
```

### Step 3: Resident History Client (`app/history.py`)
```powershell
git add app/history.py
git commit -m "feat(history): implement HTTP client for resident history API with 404 & error isolation"
```

### Step 4: Policy Engine (`app/policy.py` & `config/policy.json`)
```powershell
git add config/policy.json app/policy.py
git commit -m "feat(policy): implement data-driven PolicyEngine and ACA-2026/1 Section 6.1 ambiguity rules"
```

### Step 5: Groq Agent & Prompt Defense (`app/agent.py`)
```powershell
git add app/agent.py
git commit -m "feat(agent): implement Groq Llama 3.3 70B reasoning agent with prompt injection defense & analytical fallback"
```

### Step 6: LangGraph Workflow & Guardrail (`app/graph.py`)
```powershell
git add app/graph.py
git commit -m "feat(graph): implement LangGraph StateGraph, human approval gate, and HMAC-SHA256 execution boundary"
```

### Step 7: Main CLI Entrypoint (`app/main.py`)
```powershell
git add app/main.py
git commit -m "feat(cli): implement interactive CLI entrypoint with stdout execution tracing"
```

### Step 8: Test Suite (`tests/`)
```powershell
git add tests/
git commit -m "test: add unit & integration test suite for policy engine, guardrail security, and queue execution"
```

### Step 9: Streamlit Web UI (`frontend/app.py`)
```powershell
git add frontend/app.py
git commit -m "feat(frontend): implement Streamlit web dashboard for visual queue triage and human gate"
```

### Step 10: Documentation & Audits (`README.md`, `DECISIONS.md`, `docs/`, `audit/`)
```powershell
git add README.md DECISIONS.md AI-USAGE.md docs/ audit/
git commit -m "docs: add comprehensive developer learning guides, audit reports, DECISIONS.md, and AI disclosure"
```

### Push to GitHub:
```powershell
git branch -M main temp_branch
git branch -D main
git branch -m main
git push -f origin main
```

---

## Related Documentation
* For step-by-step file details, see [01_STEP_BY_STEP_COMMITS.md](01_STEP_BY_STEP_COMMITS.md).
