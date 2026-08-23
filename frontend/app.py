import json
import os
import sys
import time
import datetime
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from app.models import Referral, ResidentHistory, PolicyDecisionEnum
from app.history import get_resident_history, HistoryServiceError
from app.agent import analyze_and_triage
from app.policy import PolicyEngine
from app.graph import (
    generate_approval_token,
    verify_approval_token,
    execute_action_node,
    escalate_node,
    WorkflowState,
)

load_dotenv()

st.set_page_config(
    page_title="Caseworker Morning Assistant",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .badge-allowed {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 6px 14px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .badge-approval {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 6px 14px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .badge-denied {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 6px 14px;
        border-radius: 16px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .gate-box {
        background-color: #FFFBEB;
        border: 2px solid #F59E0B;
        border-radius: 10px;
        padding: 20px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
</style>
""",
    unsafe_allow_html=True,
)


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
    if "failed_referrals" not in st.session_state:
        st.session_state.failed_referrals = []
    if "recent_action_msg" not in st.session_state:
        st.session_state.recent_action_msg = ""


initialize_session()

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/government.png", width=64)
    st.title("Casework Controls")
    st.markdown("---")

    queue_file = st.selectbox("Referral Queue File", options=["referral-queue.json"], index=0)
    history_url = st.text_input("Resident History API URL", value=os.environ.get("HISTORY_API_URL", "http://127.0.0.1:8083"))

    mode = st.radio(
        "Mode Selection",
        options=["Interactive Human Gate", "Automated Demo Simulation"],
        index=0,
        help="Interactive mode automatically runs Section 2 & 4 referrals and pauses ONLY when Section 3 supervisor approval is required.",
    )

    auto_approve = mode == "Automated Demo Simulation"
    secret_key = os.environ.get("SECRET_KEY", "caseworker-guardrails-secret-key-2026")

    st.markdown("---")
    st.markdown("### Policy ACA-2026/1 Rules")
    st.caption("🟢 **6 Autonomous Referrals**: Section 2 (Address, Notes, Household, Flagging)")
    st.caption("🟡 **5 Protected Referrals**: Section 3 (Award, Income, Payment Details)")
    st.caption("🔴 **1 Escalated Referral**: Section 4 (Fraud Suspension RF-2026-0415)")

    if st.button("🚀 Start / Reset Morning Run", type="primary", use_container_width=True):
        st.session_state.run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                st.session_state.referrals = json.load(f)
            st.session_state.current_index = 0
            st.session_state.completed_referrals = []
            st.session_state.approved_referrals = []
            st.session_state.rejected_referrals = []
            st.session_state.escalated_referrals = []
            st.session_state.failed_referrals = []
            st.session_state.recent_action_msg = "Morning queue initialized."
            st.rerun()
        except Exception as e:
            st.error(f"Queue load error: {e}")

# Header
st.markdown('<div class="main-header">Calder County Department of Household Services</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated Morning Referral Sequence & Hard Guardrail Authority Boundary</div>', unsafe_allow_html=True)

tab_run, tab_queue, tab_escalations, tab_audit = st.tabs([
    "⚡ Morning Run Execution",
    "📋 Referral Queue (12)",
    "⚠️ Escalation Reports",
    "📊 Audit Traces & Analytics",
])

# TAB 1: MORNING RUN EXECUTION
with tab_run:
    if not st.session_state.referrals:
        st.info("Click **🚀 Start / Reset Morning Run** in the sidebar to begin processing the 12 overnight referrals.")
    else:
        referrals = st.session_state.referrals
        idx = st.session_state.current_index
        total = len(referrals)

        # Top Metric Bar
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        col_m1.metric("Total Referrals", total)
        col_m2.metric("Autonomous / Executed", len(st.session_state.completed_referrals))
        col_m3.metric("Human Approved", len(st.session_state.approved_referrals))
        col_m4.metric("Escalated", len(st.session_state.escalated_referrals))
        col_m5.metric("Queue Progress", f"{min(idx, total)} / {total}")

        st.progress(min(idx, total) / total)

        if st.session_state.recent_action_msg:
            st.toast(st.session_state.recent_action_msg)

        if idx >= total:
            st.balloons()
            st.success("🎉 **CASEWORKER MORNING RUN COMPLETE!** All 12 referrals processed under Policy ACA-2026/1.")
            
            runs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "runs")
            os.makedirs(runs_dir, exist_ok=True)
            audit_file = os.path.join(runs_dir, f"RUN_{st.session_state.run_id}.json")
            
            audit_data = {
                "run_id": st.session_state.run_id,
                "total": total,
                "completed": len(st.session_state.completed_referrals),
                "approved": len(st.session_state.approved_referrals),
                "rejected": len(st.session_state.rejected_referrals),
                "escalated": len(st.session_state.escalated_referrals),
                "failed": len(st.session_state.failed_referrals),
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            with open(audit_file, "w", encoding="utf-8") as f:
                json.dump(audit_data, f, indent=2)

        else:
            current_item = Referral(**referrals[idx])
            st.subheader(f"Processing Item {idx + 1} of {total}: `{current_item.referral_id}` — {current_item.requested_action}")

            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown("### 1. Referral Intake & Resident History")
                st.markdown(f"**Resident Ref:** `{current_item.resident_ref}` | **Source:** `{current_item.source}` ({current_item.urgency})")
                st.markdown(f"**Summary:** {current_item.summary}")
                st.markdown(f"**Requested Action:** `{current_item.requested_action}`")

                try:
                    history = get_resident_history(current_item.resident_ref, base_url=history_url)
                    st.success(f"✓ History Retrieved | Status: **{history.status}** | District: **{history.district}** | Monthly Award: **£{history.award_monthly:.2f}**")
                    with st.expander("Household & Case Event Log", expanded=False):
                        st.write("**Household:**", [h.model_dump() for h in history.household])
                        st.write("**Events:**", [e.model_dump() for e in history.events])
                except HistoryServiceError as e:
                    st.error(f"History API Error: {e}")
                    history = None

            with col_right:
                if history:
                    st.markdown("### 2. Triage & Policy Engine Boundary")
                    analysis, triage_note = analyze_and_triage(current_item, history)
                    policy_dec = PolicyEngine().evaluate(current_item.requested_action)

                    st.markdown(f"**Situation Summary:** {triage_note.situation_summary}")
                    st.markdown(f"**Policy Section:** `{policy_dec.policy_section}` ({policy_dec.policy_rule})")

                    if policy_dec.decision == PolicyDecisionEnum.ALLOWED:
                        st.markdown('<span class="badge-allowed">POLICY RESULT: ALLOWED (Section 2 Autonomous Action)</span>', unsafe_allow_html=True)
                        st.markdown(f"*{policy_dec.reason}*")
                        
                        # AUTOMATED LOOP CONTINUATION FOR ALLOWED REFERRALS
                        st.session_state.completed_referrals.append(current_item.referral_id)
                        st.session_state.recent_action_msg = f"✓ Autonomously executed {current_item.referral_id} ({current_item.requested_action})"
                        st.session_state.current_index += 1
                        time.sleep(0.3)
                        st.rerun()

                    elif policy_dec.decision == PolicyDecisionEnum.DENIED:
                        st.markdown('<span class="badge-denied">POLICY RESULT: DENIED & ESCALATED (Section 3.2/3.7/4.1 Forbidden)</span>', unsafe_allow_html=True)
                        st.markdown(f"*{policy_dec.reason}*")
                        
                        # AUTOMATED REFUSAL & ESCALATION FOR OUT-OF-AUTHORITY REFERRAL
                        state_mock: WorkflowState = {
                            "run_id": st.session_state.run_id,
                            "current_referral": current_item.model_dump(),
                            "policy_decision": policy_dec.model_dump(),
                            "triage_note": triage_note.model_dump(),
                        }
                        escalate_node(state_mock)
                        st.session_state.escalated_referrals.append(current_item.referral_id)
                        st.session_state.recent_action_msg = f"⚠️ Refused & Escalated {current_item.referral_id} (Fraud Allegation)"
                        st.session_state.current_index += 1
                        time.sleep(0.3)
                        st.rerun()

                    elif policy_dec.decision == PolicyDecisionEnum.APPROVAL_REQUIRED:
                        st.markdown('<span class="badge-approval">POLICY RESULT: APPROVAL REQUIRED (Section 3 Protected Action)</span>', unsafe_allow_html=True)
                        st.markdown(f"*{policy_dec.reason}*")

                        st.markdown("""
                        <div class="gate-box">
                            <h4 style="color:#92400E; margin-top:0;">🔒 HARD APPROVAL GATE ACTIVE</h4>
                            <p><b>*** NO ACTION HAS BEEN EXECUTED. ***</b></p>
                            <p>This action modifies resident benefit amounts or payment bank details. Under Policy ACA-2026/1 Section 3, a human supervisor must authorize this action before execution.</p>
                        </div>
                        """, unsafe_allow_html=True)

                        if auto_approve:
                            st.success("[AUTO-APPROVE DEMO SIMULATION] Supervisor Consent Issued.")
                            token = generate_approval_token(current_item.referral_id, current_item.requested_action, st.session_state.run_id, secret_key)
                            state_mock: WorkflowState = {
                                "run_id": st.session_state.run_id,
                                "secret_key": secret_key,
                                "current_referral": current_item.model_dump(),
                                "policy_decision": policy_dec.model_dump(),
                                "approval_token": token.model_dump(),
                            }

                            execute_action_node(state_mock)
                            st.session_state.completed_referrals.append(current_item.referral_id)
                            st.session_state.approved_referrals.append(current_item.referral_id)
                            st.session_state.recent_action_msg = f"✓ Approved & Executed {current_item.referral_id}"
                            st.session_state.current_index += 1
                            time.sleep(0.3)
                            st.rerun()

                        else:
                            # INTERACTIVE HUMAN SUPERVISOR DECISION BUTTONS
                            col_app, col_rej = st.columns(2)
                            with col_app:
                                if st.button("✅ Approve & Issue HMAC Token", type="primary", use_container_width=True):
                                    token = generate_approval_token(current_item.referral_id, current_item.requested_action, st.session_state.run_id, secret_key)
                                    state_mock: WorkflowState = {
                                        "run_id": st.session_state.run_id,
                                        "secret_key": secret_key,
                                        "current_referral": current_item.model_dump(),
                                        "policy_decision": policy_dec.model_dump(),
                                        "approval_token": token.model_dump(),
                                    }

                                    execute_action_node(state_mock)
                                    st.session_state.completed_referrals.append(current_item.referral_id)
                                    st.session_state.approved_referrals.append(current_item.referral_id)
                                    st.session_state.recent_action_msg = f"✓ Approved & Executed {current_item.referral_id}"
                                    st.session_state.current_index += 1
                                    st.rerun()

                            with col_rej:
                                if st.button("✖ Reject & Escalate", use_container_width=True):
                                    state_mock: WorkflowState = {
                                        "run_id": st.session_state.run_id,
                                        "current_referral": current_item.model_dump(),
                                        "policy_decision": policy_dec.model_dump(),
                                        "triage_note": triage_note.model_dump(),
                                    }
                                    escalate_node(state_mock)
                                    st.session_state.escalated_referrals.append(current_item.referral_id)
                                    st.session_state.rejected_referrals.append(current_item.referral_id)
                                    st.session_state.recent_action_msg = f"✖ Supervisor Rejected {current_item.referral_id}"
                                    st.session_state.current_index += 1
                                    st.rerun()

# TAB 2: REFERRAL QUEUE OVERVIEW
with tab_queue:
    st.subheader("Overnight Referral Queue (12 Referrals)")
    if os.path.exists(queue_file):
        with open(queue_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        st.dataframe(data, use_container_width=True)

# TAB 3: ESCALATION REPORTS
with tab_escalations:
    st.subheader("Escalation Reports (`artifacts/escalations/`)")
    esc_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "escalations")
    if os.path.exists(esc_dir):
        files = [f for f in os.listdir(esc_dir) if f.endswith(".json")]
        if not files:
            st.info("No escalation artifacts generated yet.")
        else:
            for fname in files:
                with st.expander(f"Escalation Report: {fname}", expanded=True):
                    with open(os.path.join(esc_dir, fname), "r", encoding="utf-8") as f:
                        st.json(json.load(f))

# TAB 4: AUDIT TRACES & ANALYTICS
with tab_audit:
    st.subheader("Audit Logs (`artifacts/runs/`)")
    runs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "runs")
    if os.path.exists(runs_dir):
        run_files = [f for f in os.listdir(runs_dir) if f.endswith(".json")]
        if not run_files:
            st.info("No run audit artifacts generated yet.")
        else:
            selected_run = st.selectbox("Select Audit Run File", run_files)
            if selected_run:
                with open(os.path.join(runs_dir, selected_run), "r", encoding="utf-8") as f:
                    st.json(json.load(f))
