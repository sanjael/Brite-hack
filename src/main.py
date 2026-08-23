import argparse
import datetime
import logging
import os
import sys
from dotenv import load_dotenv

from src.policy.engine import PolicyEngine
from src.tools.history_client import HistoryClient, HistoryClientError
from src.tools.executor import ControlledExecutor
from src.approval.gate import HumanApprovalGate
from src.escalation.manager import EscalationManager
from src.audit.logger import AuditLogger
from src.agent.graph import build_caseworker_graph
from src.agent.state import CaseworkerState

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("caseworker_main")


def main():
    parser = argparse.ArgumentParser(
        description="Brite Spark 2026 — Agentic AI / Guardrails: The Caseworker's Morning"
    )
    parser.add_argument(
        "--queue-file",
        default="referral-queue.json",
        help="Path to referral queue JSON file (default: referral-queue.json)",
    )
    parser.add_argument(
        "--history-url",
        default=os.environ.get("HISTORY_API_URL", "http://127.0.0.1:8083"),
        help="Resident History API base URL (default: http://127.0.0.1:8083)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Automatically approve supervisor approval requests for non-interactive demo testing",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with auto-approval and detailed trace display",
    )
    args = parser.parse_args()

    auto_approve = args.auto_approve or args.demo
    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    secret_key = os.environ.get("SECRET_KEY", "caseworker-guardrails-secret-key-2026")

    print("\n" + "=" * 70)
    print(" CALDER COUNTY DEPARTMENT OF HOUSEHOLD SERVICES ")
    print(" Automated Casework Assistant — Morning Referral Run ")
    print(" Policy Reference: ACA-2026/1 (Amended by ACA-2026/2) ")
    print("=" * 70)
    print(f"Run ID:            {run_id}")
    print(f"Referral Queue:    {args.queue_file}")
    print(f"History API:       {args.history_url}")
    print(f"Human Approval:    {'[AUTO-APPROVE]' if auto_approve else '[INTERACTIVE CLI]'}")
    print(f"LLM Provider:      Groq ({os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile')})")
    print("=" * 70 + "\n")

    # Initialize subsystems
    audit_logger = AuditLogger(run_id=run_id)
    history_client = HistoryClient(base_url=args.history_url)

    print("Checking Resident History API connectivity...")
    try:
        health = history_client.check_health()
        print(f"✓ History API Connected! ({health.get('records', 0)} resident records available)\n")
    except HistoryClientError as e:
        print(f"⚠ Warning: Could not connect to History API at {args.history_url}.")
        print("  Please ensure the history service is running: python3 services/history_service.py --port 8083")
        print(f"  Error details: {e}\n")
        sys.exit(1)

    policy_engine = PolicyEngine()
    executor = ControlledExecutor(secret_key=secret_key)
    gate = HumanApprovalGate(secret_key=secret_key, auto_approve=auto_approve)
    escalation_manager = EscalationManager()

    # Build LangGraph workflow
    graph = build_caseworker_graph(
        policy_engine=policy_engine,
        history_client=history_client,
        executor=executor,
        gate=gate,
        escalation_manager=escalation_manager,
        audit_logger=audit_logger,
    )

    initial_state: CaseworkerState = {
        "run_id": run_id,
        "referral_queue_file": args.queue_file,
        "history_api_url": args.history_url,
    }

    # Execute workflow
    final_state = graph.invoke(initial_state)

    # Output Summary
    print("\n" + "=" * 70)
    print(" CASEWORKER MORNING RUN COMPLETE ")
    print("=" * 70)
    print(f"Run ID:                 {run_id}")
    print(f"Total Referrals:        {final_state.get('total_referrals', 0)}")
    print(f"Completed Autonomously: {len(final_state.get('completed_referrals', []))}")
    print(f"Approved by Supervisor: {len(final_state.get('approved_referrals', []))}")
    print(f"Rejected by Supervisor: {len(final_state.get('rejected_referrals', []))}")
    print(f"Escalated (Forbidden):  {len(final_state.get('escalated_referrals', []))}")
    print(f"Handoffs (Caseworker):  {len(final_state.get('handoff_referrals', []))}")
    print(f"Errors / Failures:      {len(final_state.get('failed_referrals', []))}")
    print("-" * 70)
    print(f"Audit Trace File:       {audit_logger.run_file_path}")
    print(f"Escalation Directory:   {escalation_manager.output_dir}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
