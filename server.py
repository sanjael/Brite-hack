#!/usr/bin/env python3
"""
Calder County DHS — Automated Casework Assistant
Unified Web API Server & Static Frontend Host (Port 8080)
"""

import os
import sys
import json
import mimetypes
import argparse
import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# Ensure repository root is on sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

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
from app.security_scanner import scan_ingress_security

load_dotenv()

SECRET_KEY = os.environ.get("SECRET_KEY", "caseworker-guardrails-secret-key-2026")
HISTORY_API_URL = os.environ.get("HISTORY_API_URL", "http://127.0.0.1:8083")
WEB_DIR = os.path.join(ROOT_DIR, "web")


def fetch_history_with_fallback(resident_ref: str, base_url: str = HISTORY_API_URL) -> ResidentHistory:
    """Attempts network HTTP API call first; if offline, falls back seamlessly to local dataset."""
    try:
        return get_resident_history(resident_ref, base_url=base_url, timeout=2.0)
    except Exception:
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
        raise HistoryServiceError(f"Unable to retrieve history for resident '{resident_ref}'.")


class CaseworkerAPIHandler(BaseHTTPRequestHandler):
    server_version = "CaseworkerAssistantAPI/2.0"

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def _read_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(body)
        except Exception:
            return {}

    def _send_json(self, data, status=200):
        self._set_headers(status, "application/json")
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def _send_error(self, message, status=400):
        self._send_json({"error": True, "message": message}, status=status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # --- API ENDPOINTS ---
        if path == "/api/health":
            self._send_json({
                "status": "online",
                "service": "Calder County DHS Caseworker API",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            })
            return

        if path == "/api/queue":
            queue_file = os.path.join(ROOT_DIR, "referral-queue.json")
            if os.path.exists(queue_file):
                with open(queue_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._send_json({"queue": data, "count": len(data)})
            else:
                self._send_error("Referral queue file not found", 404)
            return

        if path.startswith("/api/resident/"):
            resident_ref = path.split("/")[-1].strip()
            try:
                hist = fetch_history_with_fallback(resident_ref)
                has_minor, unknown_state, evidence = check_household_minor(hist.household)
                hist_dict = hist.model_dump()
                hist_dict["has_minor"] = has_minor
                hist_dict["household_evidence"] = evidence
                self._send_json(hist_dict)
            except Exception as e:
                self._send_error(str(e), 404)
            return

        if path == "/api/artifacts":
            artifacts_data = {"handoffs": [], "escalations": [], "runs": []}
            handoff_dir = os.path.join(ROOT_DIR, "artifacts", "handoffs")
            esc_dir = os.path.join(ROOT_DIR, "artifacts", "escalations")
            runs_dir = os.path.join(ROOT_DIR, "artifacts", "runs")

            if os.path.exists(handoff_dir):
                for f in sorted(os.listdir(handoff_dir)):
                    if f.endswith(".json"):
                        with open(os.path.join(handoff_dir, f), "r", encoding="utf-8") as fp:
                            artifacts_data["handoffs"].append(json.load(fp))

            if os.path.exists(esc_dir):
                for f in sorted(os.listdir(esc_dir)):
                    if f.endswith(".json"):
                        with open(os.path.join(esc_dir, f), "r", encoding="utf-8") as fp:
                            artifacts_data["escalations"].append(json.load(fp))

            if os.path.exists(runs_dir):
                for f in sorted(os.listdir(runs_dir)):
                    if f.endswith(".json"):
                        with open(os.path.join(runs_dir, f), "r", encoding="utf-8") as fp:
                            artifacts_data["runs"].append(json.load(fp))

            self._send_json(artifacts_data)
            return

        # --- STATIC FILE SERVING ---
        if path == "/" or path == "":
            filepath = os.path.join(WEB_DIR, "index.html")
        else:
            rel_path = path.lstrip("/")
            filepath = os.path.join(WEB_DIR, rel_path)

        if os.path.exists(filepath) and os.path.isfile(filepath):
            mime_type, _ = mimetypes.guess_type(filepath)
            if not mime_type:
                mime_type = "application/octet-stream"
            with open(filepath, "rb") as f:
                content = f.read()
            self._set_headers(200, mime_type)
            self.wfile.write(content)
        else:
            self._send_error(f"File not found: {path}", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        # 0. SECURITY & PROMPT INJECTION SCANNER (INNOVATION MODULE)
        if path == "/api/security_scan":
            text = body.get("text", "")
            scan_result = scan_ingress_security(text)
            self._send_json(scan_result.model_dump())
            return

        # 1. EVALUATE ACTION POLICY
        if path == "/api/evaluate_action":
            action = body.get("action", "")
            decision = PolicyEngine().evaluate(action)
            self._send_json(decision.model_dump())
            return

        # 2. EVALUATE HOUSEHOLD MINOR POLICY (ACA-2026/2)
        if path == "/api/evaluate_household":
            household = body.get("household", [])
            action = body.get("action", "Draft triage note")
            decision, evidence = PolicyEngine().evaluate_household(household, action)
            self._send_json({
                "decision": decision.model_dump() if decision else None,
                "has_minor": decision is not None and decision.decision == PolicyDecisionEnum.HANDOFF_REQUIRED,
                "evidence": evidence,
            })
            return

        # 3. AI TRIAGE & REASONING GENERATOR
        if path == "/api/triage":
            referral_dict = body.get("referral")
            history_dict = body.get("history")
            if not referral_dict or not history_dict:
                self._send_error("Missing referral or history data")
                return
            try:
                ref = Referral(**referral_dict)
                hist = ResidentHistory(**history_dict)
                analysis, triage = analyze_and_triage(ref, hist)
                self._send_json({
                    "analysis": analysis,
                    "triage_note": triage.model_dump(),
                })
            except Exception as e:
                self._send_error(f"Triage generation error: {e}")
            return

        # 4. GENERATE SUPERVISOR HMAC APPROVAL TOKEN
        if path == "/api/generate_token":
            ref_id = body.get("referral_id")
            action = body.get("action")
            run_id = body.get("run_id", "LIVE-RUN")
            if not ref_id or not action:
                self._send_error("Missing referral_id or action")
                return
            token = generate_approval_token(ref_id, action, run_id, SECRET_KEY)
            self._send_json(token.model_dump())
            return

        # 5. EXECUTE ACTION (Hard Security Boundary)
        if path == "/api/execute":
            try:
                res = execute_action_node(body)
                self._send_json(res)
            except Exception as e:
                self._send_error(str(e), 403)
            return

        # 6. ESCALATE ACTION (Section 4 Prohibition)
        if path == "/api/escalate":
            try:
                res = escalate_node(body)
                self._send_json(res)
            except Exception as e:
                self._send_error(str(e), 500)
            return

        # 7. CREATE CASEWORKER HANDOFF ARTIFACT (ACA-2026/2 Section 3.9)
        if path == "/api/create_handoff":
            try:
                res = create_handoff_node(body)
                self._send_json(res)
            except Exception as e:
                self._send_error(str(e), 500)
            return

        # 8. SAVE COMPLETE RUN AUDIT
        if path == "/api/save_run":
            run_id = body.get("run_id", datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
            runs_dir = os.path.join(ROOT_DIR, "artifacts", "runs")
            os.makedirs(runs_dir, exist_ok=True)
            audit_file = os.path.join(runs_dir, f"RUN_{run_id}.json")
            with open(audit_file, "w", encoding="utf-8") as f:
                json.dump(body, f, indent=2)
            self._send_json({"saved": True, "file": audit_file})
            return

        self._send_error("Invalid API endpoint", 404)


def run_server(port=8080):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    os.makedirs(WEB_DIR, exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "artifacts", "runs"), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "artifacts", "handoffs"), exist_ok=True)
    os.makedirs(os.path.join(ROOT_DIR, "artifacts", "escalations"), exist_ok=True)

    server = ThreadingHTTPServer(("0.0.0.0", port), CaseworkerAPIHandler)
    print("\n=======================================================")
    print("Calder County DHS Caseworker Web Server Active")
    print(f"Local Web App URL:  http://localhost:{port}")
    print(f"REST API Base:      http://localhost:{port}/api")
    print("=======================================================\n")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calder County DHS Caseworker Web Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()
    run_server(args.port)
