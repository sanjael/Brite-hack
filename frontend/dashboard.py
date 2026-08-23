import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
frontend_dir = os.path.abspath(os.path.dirname(__file__))

# 1. Remove frontend directory from sys.path completely so 'import app' finds the root 'app' package
sys.path = [p for p in sys.path if os.path.abspath(p) != frontend_dir]

# 2. Add ROOT_DIR to front of sys.path
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 3. If 'app' was already loaded as the frontend script, remove it from sys.modules
if "app" in sys.modules and getattr(sys.modules["app"], "__file__", "").startswith(frontend_dir):
    del sys.modules["app"]

import json
import time
import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from app.models import (
    Referral,
    ResidentHistory,
    HouseholdMember,
    CaseEvent,
    PolicyDecision,
    PolicyDecisionEnum,
    TriageNote,
    ApprovalToken,
)
from app.history import get_resident_history, HistoryServiceError
from app.agent import analyze_and_triage
from app.policy import PolicyEngine, check_household_minor, calculate_age
from app.graph import (
    generate_approval_token,
    verify_approval_token,
    execute_action_node,
    escalate_node,
    create_handoff_node,
    WorkflowState,
)

load_dotenv()

# --- STREAMLIT CONFIGURATION ---
st.set_page_config(
    page_title="Calder County DHS — Caseworker Morning Assistant",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- MODERN EXECUTIVE DESIGN SYSTEM & CSS ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    code, pre, .mono-text {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 95%;
    }

    /* Top Executive Header */
    .gov-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }
    .gov-header-title {
        font-size: 1.75rem;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.02em;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .gov-header-sub {
        font-size: 0.92rem;
        color: #94A3B8;
        font-weight: 500;
        margin-top: 4px;
    }
    .gov-badge-live {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid #10B981;
        color: #34D399;
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .gov-badge-live::before {
        content: "";
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10B981;
    }

    /* KPI Metric Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 14px;
        margin-bottom: 22px;
    }
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.06);
    }
    .kpi-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.2;
    }
    .kpi-subtitle {
        font-size: 0.75rem;
        color: #94A3B8;
        margin-top: 4px;
    }

    /* Stepper Workflow Stage Tracker */
    .stepper-container {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 22px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        overflow-x: auto;
        gap: 12px;
    }
    .step-item {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 0.86rem;
        font-weight: 600;
        color: #64748B;
        white-space: nowrap;
    }
    .step-item.active {
        color: #4F46E5;
        font-weight: 700;
    }
    .step-item.completed {
        color: #10B981;
    }
    .step-circle {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: #E2E8F0;
        color: #475569;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .step-item.active .step-circle {
        background: #4F46E5;
        color: #FFFFFF;
        box-shadow: 0 0 10px rgba(79, 70, 229, 0.4);
    }
    .step-item.completed .step-circle {
        background: #10B981;
        color: #FFFFFF;
    }

    /* Cards & Containers */
    .casework-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03);
    }
    .casework-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 12px;
        margin-bottom: 16px;
    }
    .casework-card-title {
        font-size: 1.12rem;
        font-weight: 700;
        color: #0F172A;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Status Badges */
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }
    .badge-allowed {
        background-color: #ECFDF5;
        color: #065F46;
        border: 1px solid #A7F3D0;
    }
    .badge-approval {
        background-color: #FFFBEB;
        color: #92400E;
        border: 1px solid #FDE68A;
    }
    .badge-denied {
        background-color: #FEF2F2;
        color: #991B1B;
        border: 1px solid #FECACA;
    }
    .badge-handoff {
        background-color: #EFF6FF;
        color: #1E40AF;
        border: 1px solid #BFDBFE;
    }
    .badge-urgency-high {
        background-color: #FEF2F2;
        color: #B91C1C;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 3px 8px;
        border-radius: 6px;
    }
    .badge-urgency-standard {
        background-color: #F1F5F9;
        color: #475569;
        font-weight: 600;
        font-size: 0.75rem;
        padding: 3px 8px;
        border-radius: 6px;
    }
    .badge-minor {
        background-color: #FEF3C7;
        color: #B45309;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 2px 7px;
        border-radius: 4px;
        border: 1px solid #FCD34D;
    }

    /* Cryptographic Gate Box */
    .gate-box-secure {
        background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
        border: 2px solid #F59E0B;
        border-radius: 12px;
        padding: 20px 22px;
        margin-top: 18px;
        margin-bottom: 18px;
        box-shadow: 0 4px 15px rgba(245, 158, 11, 0.12);
    }
    .gate-box-title {
        color: #92400E;
        font-size: 1.15rem;
        font-weight: 800;
        margin-top: 0;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .gate-security-notice {
        background: #FFFFFF;
        border: 1px dashed #D97706;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 0.85rem;
        color: #78350F;
        font-weight: 600;
        margin-top: 10px;
        margin-bottom: 12px;
    }

    /* Handoff Notice Box */
    .handoff-box {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border: 2px solid #3B82F6;
        border-radius: 12px;
        padding: 20px 22px;
        margin-top: 18px;
        margin-bottom: 18px;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.12);
    }
    .handoff-box-title {
        color: #1E40AF;
        font-size: 1.15rem;
        font-weight: 800;
        margin-top: 0;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Timeline Items */
    .timeline-item {
        border-left: 2px solid #E2E8F0;
        padding-left: 14px;
        padding-bottom: 12px;
        position: relative;
    }
    .timeline-item::before {
        content: "";
        position: absolute;
        left: -5px;
        top: 2px;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #6366F1;
    }
    .timeline-date {
        font-size: 0.75rem;
        font-weight: 700;
        color: #64748B;
    }
    .timeline-type {
        font-size: 0.88rem;
        font-weight: 600;
        color: #1E293B;
    }
    .timeline-desc {
        font-size: 0.82rem;
        color: #475569;
    }

    /* Custom Streamlit Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        white-space: pre-wrap;
        background-color: #F8FAFC;
        border-radius: 8px 8px 0px 0px;
        border: 1px solid transparent;
        padding: 10px 18px;
        color: #475569;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #4F46E5 !important;
        border: 1px solid #E2E8F0 !important;
        border-bottom: 2px solid #4F46E5 !important;
        font-weight: 700 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- DATA & SESSION STATE INITIALIZATION ---
def initialize_session():
    if "run_id" not in st.session_state:
        st.session_state.run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if "referrals" not in st.session_state:
        st.session_state.referrals = []
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "completed_referrals" not in st.session_state:
        st.session_state.completed_referrals = []
    if "approved_referrals" not in st.session_state:
        st.session_state.approved_referrals = []
    if "rejected_referrals" not in st.session_state:
        st.session_state.rejected_referrals = []
    if "escalated_referrals" not in st.session_state:
        st.session_state.escalated_referrals = []
    if "handoff_referrals" not in st.session_state:
        st.session_state.handoff_referrals = []
    if "failed_referrals" not in st.session_state:
        st.session_state.failed_referrals = []
    if "recent_action_msg" not in st.session_state:
        st.session_state.recent_action_msg = ""
    if "execution_logs" not in st.session_state:
        st.session_state.execution_logs = []
    if "auto_stepping" not in st.session_state:
        st.session_state.auto_stepping = False


initialize_session()


# --- ROBUST RESIDENT HISTORY LOADER WITH LOCAL FALLBACK ---
def fetch_history_with_fallback(resident_ref: str, base_url: str) -> ResidentHistory:
    """Attempts network HTTP API call first; if offline, falls back seamlessly to local dataset."""
    try:
        return get_resident_history(resident_ref, base_url=base_url, timeout=2.0)
    except Exception:
        # Fallback to local _history_data.json
        local_path = os.path.join(ROOT_DIR, "services", "_history_data.json")
        if os.path.exists(local_path):
            with open(local_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rec = data.get(resident_ref)
            if rec:
                return ResidentHistory(
                    resident_ref=rec["resident_ref"],
                    status=rec.get("status", "Active"),
                    benefit_code=rec.get("benefit_code", "UNKNOWN"),
                    district=rec.get("district", "UNKNOWN"),
                    award_monthly=float(rec.get("award_monthly", 0.0)),
                    household=[HouseholdMember(**h) for h in rec.get("household", [])],
                    events=[CaseEvent(**e) for e in rec.get("events", [])],
                )
        raise HistoryServiceError(f"Unable to retrieve history for resident '{resident_ref}' from API or local fallback.")


# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown(
        """
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
        <div style="background:#0F172A; padding:8px; border-radius:10px; display:flex; align-items:center; justify-content:center;">
            <span style="font-size:1.6rem;">🏛️</span>
        </div>
        <div>
            <div style="font-size:1.1rem; font-weight:800; color:#0F172A; line-height:1.1;">Calder County</div>
            <div style="font-size:0.75rem; color:#64748B; font-weight:600; text-transform:uppercase;">Department of Household Services</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.caption("Automated Casework Assistant — Morning Referral Run")
    st.markdown("---")

    st.markdown("#### ⚙️ Configuration & Environment")
    queue_file = st.selectbox("Referral Queue Source", options=["referral-queue.json"], index=0)
    history_url = st.text_input("Resident History API URL", value=os.environ.get("HISTORY_API_URL", "http://127.0.0.1:8083"))
    
    # API Health Check Indicator
    api_online = False
    try:
        import urllib.request
        req = urllib.request.Request(f"{history_url.rstrip('/')}/health", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            if resp.status == 200:
                api_online = True
    except Exception:
        api_online = False

    if api_online:
        st.markdown('<span style="color:#059669; font-weight:700; font-size:0.8rem;">● Resident History API Online (:8083)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#D97706; font-weight:600; font-size:0.8rem;">○ Local Data Fallback Active (API Offline)</span>', unsafe_allow_html=True)

    mode = st.radio(
        "Supervisor Authorization Mode",
        options=["Interactive Human Gate", "Automated Demo Simulation"],
        index=0,
        help="Interactive mode executes safe cases automatically and pauses ONLY when Section 3 supervisor approval is required.",
    )
    auto_approve = mode == "Automated Demo Simulation"
    secret_key = os.environ.get("SECRET_KEY", "caseworker-guardrails-secret-key-2026")

    st.markdown("---")
    st.markdown("#### 📜 Policy Framework")
    st.markdown(
        """
    - **Policy ACA-2026/1**: Deterministic Action Authority
    - **Policy ACA-2026/2**: Minor Household Restriction (§3.9)
    - **Section 2**: Autonomous Allowed Actions (6)
    - **Section 3**: Human Supervisor Protected Gate (5)
    - **Section 4.1**: Prohibited Fraud Escalations (1)
    """
    )
    st.markdown("---")

    if st.button("🚀 Start / Reset Morning Queue", type="primary", use_container_width=True):
        st.session_state.run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            queue_full_path = os.path.join(ROOT_DIR, queue_file)
            with open(queue_full_path, "r", encoding="utf-8") as f:
                st.session_state.referrals = json.load(f)
            st.session_state.current_index = 0
            st.session_state.completed_referrals = []
            st.session_state.approved_referrals = []
            st.session_state.rejected_referrals = []
            st.session_state.escalated_referrals = []
            st.session_state.handoff_referrals = []
            st.session_state.failed_referrals = []
            st.session_state.execution_logs = []
            st.session_state.recent_action_msg = "Morning queue initialized with 12 referrals."
            st.session_state.auto_stepping = False
            st.rerun()
        except Exception as e:
            st.error(f"Error loading queue: {e}")


# --- TOP EXECUTIVE HEADER ---
st.markdown(
    f"""
<div class="gov-header">
    <div>
        <div class="gov-header-title">
            <span>🏛️</span> Calder County Department of Household Services
        </div>
        <div class="gov-header-sub">
            Automated Casework Assistant — Morning Referral Triage & Security Guardrail Console
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:10px;">
        <span class="gov-badge-live">SYSTEM ACTIVE</span>
        <div style="background:#334155; color:#E2E8F0; padding:6px 12px; border-radius:8px; font-size:0.8rem; font-family:'JetBrains Mono', monospace;">
            RUN ID: {st.session_state.run_id}
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# --- TOP KPI METRICS BAR ---
referrals = st.session_state.referrals
idx = st.session_state.current_index
total = len(referrals) if referrals else 12

autonomous_count = len(st.session_state.completed_referrals) - len(st.session_state.approved_referrals)
approved_count = len(st.session_state.approved_referrals)
escalated_count = len(st.session_state.escalated_referrals)
handoff_count = len(st.session_state.handoff_referrals)
processed_count = min(idx, total) if referrals else 0

st.markdown(
    f"""
<div class="kpi-container">
    <div class="kpi-card" style="border-left: 4px solid #4F46E5;">
        <div class="kpi-label">Queue Items</div>
        <div class="kpi-value">{total}</div>
        <div class="kpi-subtitle">Overnight Intake</div>
    </div>
    <div class="kpi-card" style="border-left: 4px solid #10B981;">
        <div class="kpi-label">Autonomous (Sec 2)</div>
        <div class="kpi-value" style="color: #059669;">{max(0, autonomous_count)}</div>
        <div class="kpi-subtitle">No Gate Required</div>
    </div>
    <div class="kpi-card" style="border-left: 4px solid #F59E0B;">
        <div class="kpi-label">Supervisor Gates (Sec 3)</div>
        <div class="kpi-value" style="color: #D97706;">{approved_count}</div>
        <div class="kpi-subtitle">Cryptographic HMAC</div>
    </div>
    <div class="kpi-card" style="border-left: 4px solid #3B82F6;">
        <div class="kpi-label">Minor Handoffs (Sec 3.9)</div>
        <div class="kpi-value" style="color: #2563EB;">{handoff_count}</div>
        <div class="kpi-subtitle">ACA-2026/2 Guardrail</div>
    </div>
    <div class="kpi-card" style="border-left: 4px solid #F43F5E;">
        <div class="kpi-label">Escalated / Refused (Sec 4)</div>
        <div class="kpi-value" style="color: #E11D48;">{escalated_count}</div>
        <div class="kpi-subtitle">Hard Prohibitions</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# --- TAB NAVIGATION ---
tab_run, tab_queue, tab_policy, tab_artifacts, tab_analytics = st.tabs(
    [
        "⚡ Morning Run Execution",
        "📋 Referral Queue Explorer",
        "🛡️ Policy & Guardrail Matrix",
        "📁 Handoffs & Escalations",
        "📊 Audit Traces & Analytics",
    ]
)


# ==============================================================================
# TAB 1: MORNING RUN EXECUTION
# ==============================================================================
with tab_run:
    if not referrals:
        st.markdown(
            """
        <div style="background:#FFFFFF; border:2px dashed #CBD5E1; border-radius:14px; padding:40px; text-align:center; margin:20px 0;">
            <div style="font-size:3rem; margin-bottom:12px;">🌅</div>
            <h3 style="color:#0F172A; margin-bottom:8px; font-weight:800;">Morning Referral Run Ready to Initialize</h3>
            <p style="color:#64748B; max-width:540px; margin:0 auto 20px auto; font-size:0.95rem;">
                The overnight queue contains 12 referrals awaiting resident history reconciliation, minor safeguard evaluation (ACA-2026/2), AI triage reasoning, and cryptographic policy execution.
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
        with col_c2:
            if st.button("🚀 Launch 12-Referral Morning Sequence", type="primary", use_container_width=True):
                queue_full_path = os.path.join(ROOT_DIR, queue_file)
                with open(queue_full_path, "r", encoding="utf-8") as f:
                    st.session_state.referrals = json.load(f)
                st.session_state.current_index = 0
                st.session_state.completed_referrals = []
                st.session_state.approved_referrals = []
                st.session_state.rejected_referrals = []
                st.session_state.escalated_referrals = []
                st.session_state.handoff_referrals = []
                st.session_state.failed_referrals = []
                st.session_state.execution_logs = []
                st.session_state.recent_action_msg = "Morning queue initialized."
                st.rerun()

    else:
        # Progress Bar & Quick Stepper
        progress_val = min(idx, total) / total
        st.progress(progress_val)
        
        # Toast notifications
        if st.session_state.recent_action_msg:
            st.toast(st.session_state.recent_action_msg)

        if idx >= total:
            # RUN COMPLETE BANNER
            st.balloons()
            st.markdown(
                f"""
            <div style="background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%); border:2px solid #10B981; border-radius:14px; padding:28px; text-align:center; margin:16px 0;">
                <div style="font-size:2.8rem; margin-bottom:8px;">🎉</div>
                <h2 style="color:#065F46; font-weight:800; margin:0 0 6px 0;">CASEWORKER MORNING RUN COMPLETE</h2>
                <p style="color:#047857; font-size:1rem; margin:0 auto 16px auto; max-width:650px;">
                    All 12 overnight referrals have been successfully processed, evaluated under Policy ACA-2026/1 & ACA-2026/2, and logged to the deterministic audit record.
                </p>
                <div style="display:inline-flex; gap:16px; font-family:'JetBrains Mono', monospace; font-size:0.85rem; background:#FFFFFF; padding:8px 18px; border-radius:8px; border:1px solid #A7F3D0;">
                    <span>✓ Autonomous: <b>{max(0, autonomous_count)}</b></span>
                    <span>✓ Approved: <b>{approved_count}</b></span>
                    <span>🛡️ Handoffs: <b>{handoff_count}</b></span>
                    <span>⚠️ Escalated: <b>{escalated_count}</b></span>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Persist Run Summary Artifact
            runs_dir = os.path.join(ROOT_DIR, "artifacts", "runs")
            os.makedirs(runs_dir, exist_ok=True)
            audit_file = os.path.join(runs_dir, f"RUN_{st.session_state.run_id}.json")
            audit_data = {
                "run_id": st.session_state.run_id,
                "total": total,
                "completed": len(st.session_state.completed_referrals),
                "approved": len(st.session_state.approved_referrals),
                "rejected": len(st.session_state.rejected_referrals),
                "escalated": len(st.session_state.escalated_referrals),
                "handoffs": len(st.session_state.handoff_referrals),
                "failed": len(st.session_state.failed_referrals),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            with open(audit_file, "w", encoding="utf-8") as f:
                json.dump(audit_data, f, indent=2)

        else:
            # CURRENT REFERRAL PROCESSING
            current_raw = referrals[idx]
            current_item = Referral(**current_raw)

            # Workflow Stage Stepper
            st.markdown(
                f"""
            <div class="stepper-container">
                <div class="step-item completed">
                    <div class="step-circle">✓</div>
                    <span>1. Referral Intake</span>
                </div>
                <div class="step-item active">
                    <div class="step-circle">2</div>
                    <span>2. Resident History Lookup</span>
                </div>
                <div class="step-item active">
                    <div class="step-circle">3</div>
                    <span>3. Safeguard Evaluation</span>
                </div>
                <div class="step-item active">
                    <div class="step-circle">4</div>
                    <span>4. Policy Engine</span>
                </div>
                <div class="step-item">
                    <div class="step-circle">5</div>
                    <span>5. Hard Boundary Execution</span>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Header info for current referral
            urgency_class = "badge-urgency-high" if current_item.urgency.lower() == "high" else "badge-urgency-standard"
            
            st.markdown(
                f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <div style="font-size:1.3rem; font-weight:800; color:#0F172A;">
                    Referral Case #{idx + 1} of {total}: <span class="mono-text" style="color:#4F46E5;">{current_item.referral_id}</span>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="{urgency_class}">{current_item.urgency.upper()} URGENCY</span>
                    <span style="background:#F1F5F9; color:#334155; font-size:0.75rem; font-weight:600; padding:3px 8px; border-radius:6px;">
                        Source: {current_item.source}
                    </span>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            # Retrieve History
            try:
                history = fetch_history_with_fallback(current_item.resident_ref, base_url=history_url)
            except Exception as e:
                st.error(f"Error fetching history: {e}")
                history = None

            col_left, col_right = st.columns([1.05, 1.25])

            # LEFT COLUMN: Intake & Demographics
            with col_left:
                st.markdown(
                    f"""
                <div class="casework-card">
                    <div class="casework-card-header">
                        <div class="casework-card-title">
                            <span>📄</span> Referral Summary & Intake
                        </div>
                        <span class="mono-text" style="font-size:0.8rem; color:#64748B;">{current_item.resident_ref}</span>
                    </div>
                    <div style="margin-bottom:12px;">
                        <div style="font-size:0.78rem; font-weight:700; color:#64748B; text-transform:uppercase;">Intake Narrative</div>
                        <div style="font-size:0.92rem; color:#1E293B; line-height:1.4; margin-top:2px;">{current_item.summary}</div>
                    </div>
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 12px;">
                        <div style="font-size:0.75rem; font-weight:700; color:#475569; text-transform:uppercase;">Requested Action</div>
                        <div style="font-size:0.95rem; font-weight:700; color:#4F46E5;" class="mono-text">{current_item.requested_action}</div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                if history:
                    # Check minor composition
                    has_minor, is_unknown, evidence = check_household_minor(history.household)

                    household_html = ""
                    for member in history.household:
                        age = calculate_age(member.date_of_birth)
                        is_m = (age is not None and age < 18)
                        minor_badge = '<span class="badge-minor">👶 MINOR (<18)</span>' if is_m else '<span style="color:#64748B; font-size:0.75rem;">Adult</span>'
                        household_html += f"""
                        <tr style="border-bottom:1px solid #F1F5F9;">
                            <td style="padding:6px 8px; font-weight:600; font-size:0.85rem;">{member.name}</td>
                            <td style="padding:6px 8px; font-size:0.82rem; color:#64748B;">{member.relationship}</td>
                            <td style="padding:6px 8px; font-size:0.82rem; color:#64748B;">{member.date_of_birth}</td>
                            <td style="padding:6px 8px; font-size:0.82rem; font-weight:600;">{age if age is not None else 'N/A'}</td>
                            <td style="padding:6px 8px;">{minor_badge}</td>
                        </tr>
                        """

                    st.markdown(
                        f"""
                    <div class="casework-card">
                        <div class="casework-card-header">
                            <div class="casework-card-title">
                                <span>👤</span> Resident History & Household
                            </div>
                            <span class="badge-pill" style="background:#F1F5F9; color:#334155; font-size:0.75rem;">{history.status.upper()}</span>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px;">
                            <div style="background:#F8FAFC; padding:8px 12px; border-radius:6px; border:1px solid #E2E8F0;">
                                <div style="font-size:0.72rem; color:#64748B; font-weight:700; text-transform:uppercase;">District</div>
                                <div style="font-size:0.9rem; font-weight:700; color:#0F172A;">{history.district}</div>
                            </div>
                            <div style="background:#F8FAFC; padding:8px 12px; border-radius:6px; border:1px solid #E2E8F0;">
                                <div style="font-size:0.72rem; color:#64748B; font-weight:700; text-transform:uppercase;">Monthly Award</div>
                                <div style="font-size:0.9rem; font-weight:700; color:#0F172A;">£{history.award_monthly:.2f}</div>
                            </div>
                        </div>

                        <div style="font-size:0.78rem; font-weight:700; color:#64748B; text-transform:uppercase; margin-bottom:6px;">
                            Household Members ({len(history.household)})
                        </div>
                        <table style="width:100%; border-collapse:collapse; margin-bottom:14px;">
                            <thead>
                                <tr style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; text-align:left;">
                                    <th style="padding:5px 8px; font-size:0.72rem; color:#64748B; text-transform:uppercase;">Name</th>
                                    <th style="padding:5px 8px; font-size:0.72rem; color:#64748B; text-transform:uppercase;">Relation</th>
                                    <th style="padding:5px 8px; font-size:0.72rem; color:#64748B; text-transform:uppercase;">DOB</th>
                                    <th style="padding:5px 8px; font-size:0.72rem; color:#64748B; text-transform:uppercase;">Age</th>
                                    <th style="padding:5px 8px; font-size:0.72rem; color:#64748B; text-transform:uppercase;">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {household_html}
                            </tbody>
                        </table>

                        <details style="font-size:0.85rem; color:#475569;">
                            <summary style="cursor:pointer; font-weight:600; color:#4F46E5;">View Case Events Log ({len(history.events)} events)</summary>
                            <div style="margin-top:10px;">
                    """,
                        unsafe_allow_html=True,
                    )
                    for ev in history.events:
                        st.markdown(
                            f"""
                        <div class="timeline-item">
                            <div class="timeline-date">{ev.date}</div>
                            <div class="timeline-type">{ev.type}</div>
                            <div class="timeline-desc">{ev.detail}</div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    st.markdown("</div></details></div>", unsafe_allow_html=True)

            # RIGHT COLUMN: Policy Evaluation & Guardrails
            with col_right:
                if history:
                    # 1. Check ACA-2026/2 Minor Household Policy
                    household_decision, household_evidence = PolicyEngine().evaluate_household(history.household)

                    if household_decision and household_decision.decision == PolicyDecisionEnum.HANDOFF_REQUIRED:
                        # ACA-2026/2 RESTRICTION ACTIVE: MINOR IN HOUSEHOLD
                        st.markdown(
                            f"""
                        <div class="casework-card" style="border-top:4px solid #3B82F6;">
                            <div class="casework-card-header">
                                <div class="casework-card-title" style="color:#1E40AF;">
                                    <span>🛡️</span> ACA-2026/2 Safeguard: Minor in Household
                                </div>
                                <span class="badge-pill badge-handoff">SECTION 3.9 RESTRICTION</span>
                            </div>
                            
                            <div class="handoff-box">
                                <div class="handoff-box-title">
                                    <span>🛑</span> AI TRIAGE DRAFTING RESTRICTED
                                </div>
                                <p style="margin:0 0 8px 0; font-size:0.88rem; color:#1E3A8A;">
                                    Under <b>Policy ACA-2026/2 Section 3.9</b>, the AI model is <b>structurally prohibited</b> from drafting triage notes for any household containing persons under 18.
                                </p>
                                <div style="font-size:0.82rem; color:#1E40AF; font-weight:600;">
                                    Reason: {household_decision.reason}
                                </div>
                            </div>

                            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:14px; margin-bottom:14px;">
                                <div style="font-size:0.8rem; font-weight:700; color:#334155; margin-bottom:6px;">Handoff Checklist Artifact Generated:</div>
                                <div style="font-size:0.85rem; color:#059669;">✓ Referral Intake Registered</div>
                                <div style="font-size:0.85rem; color:#059669;">✓ Resident History Reconciled</div>
                                <div style="font-size:0.85rem; color:#059669;">✓ Minor Dependent Composition Verified</div>
                                <div style="font-size:0.85rem; color:#DC2626; font-weight:700;">✗ AI Triage Generation: BLOCKED BY POLICY</div>
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        # Create Handoff File
                        state_mock: WorkflowState = {
                            "run_id": st.session_state.run_id,
                            "current_referral": current_item.model_dump(),
                            "resident_history": history.model_dump(),
                            "policy_decision": household_decision.model_dump(),
                        }
                        create_handoff_node(state_mock)

                        if current_item.referral_id not in st.session_state.handoff_referrals:
                            st.session_state.handoff_referrals.append(current_item.referral_id)

                        col_btn1, col_btn2 = st.columns([1, 1])
                        with col_btn1:
                            if st.button("➡️ Complete Handoff & Continue", type="primary", use_container_width=True):
                                st.session_state.recent_action_msg = f"🛡️ Caseworker Handoff Created for {current_item.referral_id} (ACA-2026/2 Sec 3.9)"
                                st.session_state.current_index += 1
                                st.rerun()

                    else:
                        # SAFE HOUSEHOLD -> AI TRIAGE & ACTION POLICY EVALUATION
                        analysis, triage_note = analyze_and_triage(current_item, history)
                        policy_dec = PolicyEngine().evaluate(current_item.requested_action)

                        st.markdown(
                            f"""
                        <div class="casework-card">
                            <div class="casework-card-header">
                                <div class="casework-card-title">
                                    <span>🧠</span> AI Triage Reasoning (Llama-3.3-70B)
                                </div>
                                <span class="badge-pill badge-allowed">SAFE HOUSEHOLD</span>
                            </div>
                            <div style="margin-bottom:12px;">
                                <div style="font-size:0.75rem; font-weight:700; color:#64748B; text-transform:uppercase;">Situation Summary</div>
                                <div style="font-size:0.9rem; color:#1E293B; margin-top:2px;">{triage_note.situation_summary}</div>
                            </div>
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                                <div style="background:#F8FAFC; padding:8px 10px; border-radius:6px; border:1px solid #E2E8F0;">
                                    <div style="font-size:0.72rem; color:#64748B; font-weight:700; text-transform:uppercase;">Risk Level</div>
                                    <div style="font-size:0.88rem; font-weight:700; color:#0F172A;">{triage_note.risk_level.value.upper()}</div>
                                </div>
                                <div style="background:#F8FAFC; padding:8px 10px; border-radius:6px; border:1px solid #E2E8F0;">
                                    <div style="font-size:0.72rem; color:#64748B; font-weight:700; text-transform:uppercase;">Recommended Action</div>
                                    <div style="font-size:0.88rem; font-weight:700; color:#4F46E5;">{triage_note.recommended_action}</div>
                                </div>
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

                        # SECTION 2: AUTONOMOUS ACTION
                        if policy_dec.decision == PolicyDecisionEnum.ALLOWED:
                            st.markdown(
                                f"""
                            <div class="casework-card" style="border-top:4px solid #10B981;">
                                <div class="casework-card-header">
                                    <div class="casework-card-title" style="color:#065F46;">
                                        <span>⚡</span> Policy Evaluation: Autonomous Execution
                                    </div>
                                    <span class="badge-pill badge-allowed">SECTION {policy_dec.policy_section} ALLOWED</span>
                                </div>
                                <div style="font-size:0.88rem; color:#047857; margin-bottom:12px;">
                                    <b>Policy Rule {policy_dec.policy_rule}:</b> {policy_dec.reason}
                                </div>
                                <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:8px; padding:10px 14px; font-size:0.82rem; color:#065F46; font-weight:600;">
                                    ✓ Action permitted within caseworker automated boundary. Executing safely...
                                </div>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            if current_item.referral_id not in st.session_state.completed_referrals:
                                st.session_state.completed_referrals.append(current_item.referral_id)

                            col_btn1, col_btn2 = st.columns([1, 1])
                            with col_btn1:
                                if st.button("✓ Execute & Next Referral", type="primary", use_container_width=True):
                                    st.session_state.recent_action_msg = f"✓ Autonomously executed {current_item.referral_id} ({current_item.requested_action})"
                                    st.session_state.current_index += 1
                                    st.rerun()

                        # SECTION 4.1: PROHIBITED / FRAUD SUSPENSION ESCALATION
                        elif policy_dec.decision == PolicyDecisionEnum.DENIED:
                            st.markdown(
                                f"""
                            <div class="casework-card" style="border-top:4px solid #F43F5E;">
                                <div class="casework-card-header">
                                    <div class="casework-card-title" style="color:#991B1B;">
                                        <span>⛔</span> Policy Evaluation: Action Explicitly Prohibited
                                    </div>
                                    <span class="badge-pill badge-denied">SECTION {policy_dec.policy_section} PROHIBITED</span>
                                </div>
                                <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:8px; padding:12px 14px; margin-bottom:12px;">
                                    <div style="font-weight:700; color:#991B1B; font-size:0.9rem; margin-bottom:4px;">
                                        CRITICAL SECURITY BOUNDARY BREACH REFUSED
                                    </div>
                                    <div style="font-size:0.85rem; color:#7F1D1D;">
                                        {policy_dec.reason}
                                    </div>
                                </div>
                                <p style="font-size:0.82rem; color:#64748B;">
                                    Under Policy Sections 3.2, 3.7 & 4.1, automated suspension of welfare support is prohibited. Generating formal escalation dossier...
                                </p>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            state_mock: WorkflowState = {
                                "run_id": st.session_state.run_id,
                                "current_referral": current_item.model_dump(),
                                "policy_decision": policy_dec.model_dump(),
                                "triage_note": triage_note.model_dump(),
                            }
                            escalate_node(state_mock)

                            if current_item.referral_id not in st.session_state.escalated_referrals:
                                st.session_state.escalated_referrals.append(current_item.referral_id)

                            col_btn1, col_btn2 = st.columns([1, 1])
                            with col_btn1:
                                if st.button("⚠️ Confirm Escalation & Next Referral", type="primary", use_container_width=True):
                                    st.session_state.recent_action_msg = f"⚠️ Prohibited Action Refused & Escalated: {current_item.referral_id}"
                                    st.session_state.current_index += 1
                                    st.rerun()

                        # SECTION 3: SUPERVISOR APPROVAL REQUIRED GATE
                        elif policy_dec.decision == PolicyDecisionEnum.APPROVAL_REQUIRED:
                            st.markdown(
                                f"""
                            <div class="casework-card" style="border-top:4px solid #F59E0B;">
                                <div class="casework-card-header">
                                    <div class="casework-card-title" style="color:#92400E;">
                                        <span>🔒</span> Cryptographic Supervisor Approval Gate
                                    </div>
                                    <span class="badge-pill badge-approval">SECTION {policy_dec.policy_section} PROTECTED</span>
                                </div>
                                
                                <div class="gate-box-secure">
                                    <div class="gate-box-title">
                                        <span>🛡️</span> SUPERVISOR AUTHORIZATION REQUIRED
                                    </div>
                                    <div style="font-size:0.88rem; color:#78350F; margin-bottom:8px;">
                                        <b>Protected Action:</b> <span class="mono-text" style="font-weight:700;">{current_item.requested_action}</span>
                                    </div>
                                    <div class="gate-security-notice">
                                        ⚠️ *** NO ACTION HAS BEEN EXECUTED ***<br>
                                        Modifies resident financial awards or bank details. Requires HMAC-SHA256 signature from human supervisor.
                                    </div>
                                    <div style="font-size:0.8rem; color:#92400E;">
                                        <b>Policy Justification:</b> {policy_dec.reason}
                                    </div>
                                </div>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                            if auto_approve:
                                st.info("🤖 **Automated Demo Mode:** Supervisor consent automatically signed.")
                                token = generate_approval_token(current_item.referral_id, current_item.requested_action, st.session_state.run_id, secret_key)
                                state_mock: WorkflowState = {
                                    "run_id": st.session_state.run_id,
                                    "secret_key": secret_key,
                                    "current_referral": current_item.model_dump(),
                                    "policy_decision": policy_dec.model_dump(),
                                    "approval_token": token.model_dump(),
                                }
                                execute_action_node(state_mock)
                                if current_item.referral_id not in st.session_state.completed_referrals:
                                    st.session_state.completed_referrals.append(current_item.referral_id)
                                if current_item.referral_id not in st.session_state.approved_referrals:
                                    st.session_state.approved_referrals.append(current_item.referral_id)

                                if st.button("➡️ Continue to Next Referral", type="primary", use_container_width=True):
                                    st.session_state.recent_action_msg = f"✓ Approved & Executed {current_item.referral_id}"
                                    st.session_state.current_index += 1
                                    st.rerun()

                            else:
                                col_app, col_rej = st.columns(2)
                                with col_app:
                                    if st.button("✅ Approve & Sign HMAC Token", type="primary", use_container_width=True):
                                        token = generate_approval_token(
                                            current_item.referral_id,
                                            current_item.requested_action,
                                            st.session_state.run_id,
                                            secret_key,
                                        )
                                        state_mock: WorkflowState = {
                                            "run_id": st.session_state.run_id,
                                            "secret_key": secret_key,
                                            "current_referral": current_item.model_dump(),
                                            "policy_decision": policy_dec.model_dump(),
                                            "approval_token": token.model_dump(),
                                        }
                                        execute_action_node(state_mock)
                                        if current_item.referral_id not in st.session_state.completed_referrals:
                                            st.session_state.completed_referrals.append(current_item.referral_id)
                                        if current_item.referral_id not in st.session_state.approved_referrals:
                                            st.session_state.approved_referrals.append(current_item.referral_id)
                                        st.session_state.recent_action_msg = f"✓ Supervisor Approved & Executed {current_item.referral_id}"
                                        st.session_state.current_index += 1
                                        st.rerun()

                                with col_rej:
                                    if st.button("✖ Reject & Escalate to Board", use_container_width=True):
                                        state_mock: WorkflowState = {
                                            "run_id": st.session_state.run_id,
                                            "current_referral": current_item.model_dump(),
                                            "policy_decision": policy_dec.model_dump(),
                                            "triage_note": triage_note.model_dump(),
                                        }
                                        escalate_node(state_mock)
                                        if current_item.referral_id not in st.session_state.escalated_referrals:
                                            st.session_state.escalated_referrals.append(current_item.referral_id)
                                        if current_item.referral_id not in st.session_state.rejected_referrals:
                                            st.session_state.rejected_referrals.append(current_item.referral_id)
                                        st.session_state.recent_action_msg = f"✖ Supervisor Rejected {current_item.referral_id}"
                                        st.session_state.current_index += 1
                                        st.rerun()


# ==============================================================================
# TAB 2: REFERRAL QUEUE EXPLORER
# ==============================================================================
with tab_queue:
    st.markdown(
        """
    <div class="casework-card">
        <div class="casework-card-header">
            <div class="casework-card-title">
                <span>📋</span> Overnight Referral Intake Matrix (12 Cases)
            </div>
            <span style="font-size:0.8rem; color:#64748B;">Source of Truth: <code>referral-queue.json</code></span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    queue_full_path = os.path.join(ROOT_DIR, queue_file)
    if os.path.exists(queue_full_path):
        with open(queue_full_path, "r", encoding="utf-8") as f:
            queue_data = json.load(f)

        # Filters
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            urgency_filter = st.multiselect("Filter by Urgency", options=["All", "High", "Standard", "Low"], default=["All"])
        with col_f2:
            search_query = st.text_input("🔍 Search Referrals (ID, Resident Ref, Action, Summary)", placeholder="e.g. RF-2026-0412, Review award, R-20500...")

        filtered_queue = []
        for item in queue_data:
            if "All" not in urgency_filter and item.get("urgency") not in urgency_filter:
                continue
            if search_query:
                q = search_query.lower()
                if (
                    q not in item.get("referral_id", "").lower()
                    and q not in item.get("resident_ref", "").lower()
                    and q not in item.get("requested_action", "").lower()
                    and q not in item.get("summary", "").lower()
                ):
                    continue
            filtered_queue.append(item)

        df = pd.DataFrame(filtered_queue)
        if not df.empty:
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "referral_id": st.column_config.TextColumn("Referral ID", width="small"),
                    "received_at": st.column_config.DatetimeColumn("Received At", format="YYYY-MM-DD HH:mm"),
                    "resident_ref": st.column_config.TextColumn("Resident Ref", width="small"),
                    "source": st.column_config.TextColumn("Source Intake"),
                    "requested_action": st.column_config.TextColumn("Requested Action"),
                    "urgency": st.column_config.TextColumn("Urgency", width="small"),
                    "summary": st.column_config.TextColumn("Summary Narrative", width="large"),
                },
                hide_index=True,
            )
        else:
            st.info("No referrals matched your filter criteria.")


# ==============================================================================
# TAB 3: POLICY & GUARDRAIL MATRIX
# ==============================================================================
with tab_policy:
    st.markdown(
        """
    <div class="casework-card">
        <div class="casework-card-header">
            <div class="casework-card-title">
                <span>🛡️</span> Calder County Policy Authority Matrix (ACA-2026/1 & ACA-2026/2)
            </div>
            <span class="badge-pill badge-allowed">DETERMINISTIC ENGINE</span>
        </div>
        <p style="font-size:0.9rem; color:#475569; margin-bottom:16px;">
            The agentic reasoning model proposes caseworker triage notes, but execution is governed by hard deterministic policies.
        </p>

        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:14px;">
            <div style="background:#ECFDF5; border:1px solid #A7F3D0; border-radius:10px; padding:16px;">
                <div style="font-weight:800; color:#065F46; font-size:0.95rem; margin-bottom:6px;">
                    🟢 SECTION 2: AUTONOMOUS ACTIONS
                </div>
                <p style="font-size:0.82rem; color:#047857; margin-bottom:8px;">
                    Actions permitted without human gate.
                </p>
                <ul style="font-size:0.8rem; color:#065F46; padding-left:18px; margin:0;">
                    <li>Record change of address (2.1)</li>
                    <li>Record contact preferences (2.2)</li>
                    <li>Log received evidence (2.3)</li>
                    <li>Draft explanatory note (2.4)</li>
                    <li>Flag for contact attempt (2.5)</li>
                    <li>Review household composition (2.6)</li>
                    <li>Draft triage note for supervisor (2.7)</li>
                </ul>
            </div>

            <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:16px;">
                <div style="font-weight:800; color:#92400E; font-size:0.95rem; margin-bottom:6px;">
                    🟡 SECTION 3: SUPERVISOR APPROVAL
                </div>
                <p style="font-size:0.82rem; color:#78350F; margin-bottom:8px;">
                    Requires cryptographic HMAC token authorization.
                </p>
                <ul style="font-size:0.8rem; color:#92400E; padding-left:18px; margin:0;">
                    <li>Review award amount (3.1)</li>
                    <li>Record income changes (3.3)</li>
                    <li>Update payment bank details (3.6)</li>
                    <li>Record overpayment recovery plan (3.8)</li>
                </ul>
            </div>

            <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px; padding:16px;">
                <div style="font-weight:800; color:#1E40AF; font-size:0.95rem; margin-bottom:6px;">
                    🔵 SECTION 3.9: MINOR RESTRICTION (ACA-2026/2)
                </div>
                <p style="font-size:0.82rem; color:#1E3A8A; margin-bottom:8px;">
                    Mandatory caseworker handoff if person &lt; 18.
                </p>
                <ul style="font-size:0.8rem; color:#1E40AF; padding-left:18px; margin:0;">
                    <li>Household includes minor child: <b>Triage drafting prohibited</b></li>
                    <li>Must create handoff artifact without LLM note</li>
                </ul>
            </div>

            <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:10px; padding:16px;">
                <div style="font-weight:800; color:#991B1B; font-size:0.95rem; margin-bottom:6px;">
                    🔴 SECTION 4 &amp; 3.2: PROHIBITED ACTIONS
                </div>
                <p style="font-size:0.82rem; color:#7F1D1D; margin-bottom:8px;">
                    Forbidden side-effects escalated immediately.
                </p>
                <ul style="font-size:0.8rem; color:#991B1B; padding-left:18px; margin:0;">
                    <li>Suspend assistance on fraud allegation (3.2/3.7/4.1)</li>
                    <li>Terminate benefit award</li>
                    <li>Unknown / ambiguous actions (Rule 6.1)</li>
                </ul>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# TAB 4: HANDOFFS & ESCALATIONS ARTIFACTS
# ==============================================================================
with tab_artifacts:
    st.markdown(
        """
    <div class="casework-card">
        <div class="casework-card-header">
            <div class="casework-card-title">
                <span>📁</span> Governance & Safety Artifacts Inspector
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    art_mode = st.radio("Select Artifact Collection", options=["Caseworker Handoffs (ACA-2026/2)", "Escalation Reports (Section 4)"], horizontal=True)

    if art_mode == "Caseworker Handoffs (ACA-2026/2)":
        handoff_dir = os.path.join(ROOT_DIR, "artifacts", "handoffs")
        if os.path.exists(handoff_dir):
            files = [f for f in os.listdir(handoff_dir) if f.endswith(".json")]
            if not files:
                st.info("No handoff artifacts generated yet. Run referral `RF-2026-0412` to create a handoff.")
            else:
                for fname in files:
                    with open(os.path.join(handoff_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    with st.expander(f"🛡️ Handoff Artifact: {fname} (Resident: {data.get('resident_ref')})", expanded=True):
                        col_h1, col_h2 = st.columns([1, 1])
                        with col_h1:
                            st.markdown(f"**Referral ID:** `{data.get('referral_id')}`")
                            st.markdown(f"**Policy:** `{data.get('policy')} Section {data.get('policy_rule')}`")
                            st.markdown(f"**Status:** `{data.get('status')}`")
                            st.markdown(f"**Reason:** {data.get('reason')}")
                        with col_h2:
                            st.markdown("**Checklist Status:**")
                            for w in data.get("work_completed", []):
                                st.markdown(f"<span style='color:#059669;'>{w}</span>", unsafe_allow_html=True)
                            for w in data.get("work_not_completed", []):
                                st.markdown(f"<span style='color:#DC2626; font-weight:700;'>{w}</span>", unsafe_allow_html=True)
                        st.json(data)
        else:
            st.info("No handoff directory found.")

    else:
        esc_dir = os.path.join(ROOT_DIR, "artifacts", "escalations")
        if os.path.exists(esc_dir):
            files = [f for f in os.listdir(esc_dir) if f.endswith(".json")]
            if not files:
                st.info("No escalation artifacts generated yet. Run referral `RF-2026-0415` to trigger a fraud escalation.")
            else:
                for fname in files:
                    with open(os.path.join(esc_dir, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    with st.expander(f"⚠️ Escalation Dossier: {fname} (Action: {data.get('requested_action')})", expanded=True):
                        st.markdown(f"**Referral:** `{data.get('referral_id')}` | **Resident:** `{data.get('resident_ref')}`")
                        st.markdown(f"**Policy Section:** `{data.get('policy_section')}` ({data.get('policy_rule')})")
                        st.error(f"**Escalation Reason:** {data.get('reason')}")
                        st.json(data)
        else:
            st.info("No escalation directory found.")


# ==============================================================================
# TAB 5: AUDIT TRACES & ANALYTICS
# ==============================================================================
with tab_analytics:
    st.markdown(
        """
    <div class="casework-card">
        <div class="casework-card-header">
            <div class="casework-card-title">
                <span>📊</span> Audit Logs & System Telemetry
            </div>
            <span style="font-size:0.8rem; color:#64748B;">Audit Directory: <code>artifacts/runs/</code></span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    runs_dir = os.path.join(ROOT_DIR, "artifacts", "runs")
    if os.path.exists(runs_dir):
        run_files = [f for f in os.listdir(runs_dir) if f.endswith(".json")]
        if not run_files:
            st.info("No run audit records found yet. Complete a morning run to generate telemetry.")
        else:
            selected_run = st.selectbox("Select Audit Run Record", options=run_files, index=0)
            if selected_run:
                with open(os.path.join(runs_dir, selected_run), "r", encoding="utf-8") as f:
                    run_audit = json.load(f)

                col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                col_a1.metric("Run ID", run_audit.get("run_id", "N/A"))
                col_a2.metric("Completed", run_audit.get("completed", 0))
                col_a3.metric("Approved", run_audit.get("approved", 0))
                col_a4.metric("Escalated", run_audit.get("escalated", 0))

                st.markdown("#### Full Audit Telemetry (JSON)")
                st.json(run_audit)
    else:
        st.info("Runs directory not found.")
