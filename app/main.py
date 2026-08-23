import argparse
import datetime
import json
import os
from dotenv import load_dotenv

from app.history import get_resident_history
from app.graph import build_workflow_graph, WorkflowState

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Brite Spark 2026 — Problem 5: The Caseworker's Morning")
    parser.add_argument("--queue-file", default="referral-queue.json", help="Path to referral queue JSON file")
    parser.add_argument("--history-url", default=os.environ.get("HISTORY_API_URL", "http://127.0.0.1:8083"), help="Resident History API base URL")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve supervisor requests for demo evaluation")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode")
    args = parser.parse_args()

    auto_approve = args.auto_approve or args.demo
    run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    secret_key = os.environ.get("SECRET_KEY", "caseworker-guardrails-secret-key-2026")

    print("\n" + "=" * 60)
    print(" CALDER COUNTY DEPARTMENT OF HOUSEHOLD SERVICES ")
    print(" Automated Casework Assistant — Morning Referral Run ")
    print(" Policy Reference: ACA-2026/1 ")
    print("=" * 60)
    print(f"Run ID:          {run_id}")
    print(f"Referral Queue:  {args.queue_file}")
    print(f"History API:     {args.history_url}")
    print(f"Mode:            {'[DEMO / AUTO-APPROVE]' if auto_approve else '[INTERACTIVE CLI]'}")
    print("=" * 60 + "\n")

    try:
        get_resident_history("R-20500", base_url=args.history_url)
        print("✓ Connected to Resident History API!\n")
    except Exception as e:
        print(f"⚠ History API health check warning: {e}\n")

    graph = build_workflow_graph()
    initial_state: WorkflowState = {
        "run_id": run_id,
        "queue_file": args.queue_file,
        "history_api_url": args.history_url,
        "auto_approve": auto_approve,
        "secret_key": secret_key,
    }

    final_state = graph.invoke(initial_state)

    runs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "runs")
    os.makedirs(runs_dir, exist_ok=True)
    audit_file = os.path.join(runs_dir, f"RUN_{run_id}.json")

    run_summary = {
        "run_id": run_id,
        "total": final_state.get("total_count", 0),
        "completed": len(final_state.get("completed_referrals", [])),
        "approved": len(final_state.get("approved_referrals", [])),
        "rejected": len(final_state.get("rejected_referrals", [])),
        "escalated": len(final_state.get("escalated_referrals", [])),
        "failed": len(final_state.get("failed_referrals", [])),
        "errors": final_state.get("errors", []),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(run_summary, f, indent=2)

    print("\n" + "=" * 60)
    print(" CASEWORKER MORNING RUN COMPLETE ")
    print("=" * 60)
    print(f"Total Referrals:     {run_summary['total']}")
    print(f"Completed:           {run_summary['completed']}")
    print(f"Approved:            {run_summary['approved']}")
    print(f"Rejected:            {run_summary['rejected']}")
    print(f"Escalated:           {run_summary['escalated']}")
    print(f"Failed:              {run_summary['failed']}")
    print("-" * 60)
    print(f"Audit log artifact:  {audit_file}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
