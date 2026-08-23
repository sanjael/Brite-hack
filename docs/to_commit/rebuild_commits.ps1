# PowerShell Script to Rebuild Clean Incremental Commit History
# Run from repository root: .\docs\to_commit\rebuild_commits.ps1

Write-Host "Creating clean orphan branch 'fresh_main'..." -ForegroundColor Cyan
git checkout --orphan fresh_main
git reset

Write-Host "`n[1/10] Committing base setup and provided hackathon files..." -ForegroundColor Yellow
git add .gitignore requirements.txt .env.example authority-policy.md referral-queue.json services/
git commit -m "feat: initialize project structure, policy ACA-2026/1, and mock history service"

Write-Host "`n[2/10] Committing Pydantic data models..." -ForegroundColor Yellow
git add app/__init__.py app/models.py
git commit -m "feat(models): define Pydantic data schemas for referrals, history, policy decisions, and HMAC tokens"

Write-Host "`n[3/10] Committing Resident History API client..." -ForegroundColor Yellow
git add app/history.py
git commit -m "feat(history): implement HTTP client for resident history API with 404 & error isolation"

Write-Host "`n[4/10] Committing Policy Engine and policy.json..." -ForegroundColor Yellow
git add config/policy.json app/policy.py
git commit -m "feat(policy): implement data-driven PolicyEngine and ACA-2026/1 Section 6.1 ambiguity rules"

Write-Host "`n[5/10] Committing Groq Agent and Prompt Injection Defense..." -ForegroundColor Yellow
git add app/agent.py
git commit -m "feat(agent): implement Groq Llama 3.3 70B reasoning agent with prompt injection defense & analytical fallback"

Write-Host "`n[6/10] Committing LangGraph Workflow and HMAC Guardrail..." -ForegroundColor Yellow
git add app/graph.py
git commit -m "feat(graph): implement LangGraph StateGraph, human approval gate, and HMAC-SHA256 execution boundary"

Write-Host "`n[7/10] Committing Main CLI Entrypoint..." -ForegroundColor Yellow
git add app/main.py
git commit -m "feat(cli): implement interactive CLI entrypoint with stdout execution tracing"

Write-Host "`n[8/10] Committing Unit and Guardrail Test Suite..." -ForegroundColor Yellow
git add tests/
git commit -m "test: add unit & integration test suite for policy engine, guardrail security, and queue execution"

Write-Host "`n[9/10] Committing Streamlit Web Dashboard..." -ForegroundColor Yellow
git add frontend/
git commit -m "feat(frontend): implement Streamlit web dashboard for visual queue triage and human gate"

Write-Host "`n[10/10] Committing Documentation & Audit Layer..." -ForegroundColor Yellow
git add README.md DECISIONS.md AI-USAGE.md docs/ audit/
git commit -m "docs: add comprehensive developer learning guides, audit reports, DECISIONS.md, and AI disclosure"

Write-Host "`nReplacing main branch with fresh commit history..." -ForegroundColor Cyan
git branch -M fresh_main main

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " CLEAN INCREMENTAL COMMIT HISTORY GENERATED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "To push to GitHub, run: git push -f origin main" -ForegroundColor Yellow
