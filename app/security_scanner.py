"""
Calder County DHS — Ingress Security & Adversarial Prompt Injection Scanner
Innovation Module for Defense-in-Depth Agentic AI Guardrails
"""

import re
import base64
from typing import List, Optional
from pydantic import BaseModel, Field


class SecurityScanResult(BaseModel):
    is_safe: bool = True
    threat_level: str = "CLEAN"  # CLEAN, ELEVATED, CRITICAL
    threat_type: Optional[str] = None
    matched_signatures: List[str] = Field(default_factory=list)
    threat_summary: str = "Ingress verification passed. Zero adversarial signatures detected."
    remediation: str = "Proceed with normal policy pipeline."


# Curated Deterministic Signatures for LLM Ingress Vulnerabilities
ADVERSARIAL_RULES = [
    {
        "type": "DIRECTIVE_OVERRIDE",
        "pattern": r"(?i)(ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules|policies)|disregard\s+(policy|rules|guardrails)|override\s+(system|county|aca\-\d+)|bypass\s+(supervisor|guardrails|security))",
        "level": "CRITICAL",
        "summary": "Detected explicit attempt to override system instructions or bypass county policy boundaries."
    },
    {
        "type": "ROLE_SPOOFING_JAILBREAK",
        "pattern": r"(?i)(act\s+as\s+(an?\s+)?(unrestricted|administrator|root|dan|system\s+developer|unfiltered\s+ai)|you\s+are\s+now\s+in\s+developer\s+mode|enable\s+(god|admin|jailbreak)\s+mode)",
        "level": "CRITICAL",
        "summary": "Detected role-play evasion or developer mode jailbreak attempt targeting LLM authority."
    },
    {
        "type": "FINANCIAL_ENTITLEMENT_FORGERY",
        "pattern": r"(?i)(auto\-?approve\s+(maximum|full|\£|\$)|set\s+(award|grant|payout)\s+to\s+(\£|\$)?\s*\d{3,}|grant\s+unlimited\s+funds|force\s+approve\s+without\s+gate)",
        "level": "CRITICAL",
        "summary": "Detected attempt to force unauthorized financial benefit payouts via prompt injection."
    },
    {
        "type": "SYSTEM_PROMPT_EXTRACTION",
        "pattern": r"(?i)(repeat\s+(everything|the\s+system\s+prompt|the\s+instructions\s+above)|what\s+is\s+your\s+secret\s+key|print\s+system\s+context|output\s+system\s+directives)",
        "level": "ELEVATED",
        "summary": "Detected reconnaissance probe attempting to extract internal system prompt or secret HMAC keys."
    },
    {
        "type": "CODE_INJECTION_PROBE",
        "pattern": r"(?i)(<\s*script\b|javascript\s*:|DROP\s+TABLE|SELECT\s+\*\s+FROM|UNION\s+SELECT|exec\s*\(|eval\s*\(|;\s*rm\s+\-rf)",
        "level": "CRITICAL",
        "summary": "Detected SQL/Script/Command injection syntax embedded in casework narrative."
    }
]


def check_base64_obfuscation(text: str) -> Optional[str]:
    """Detects potential base64-encoded hidden payloads in intake narratives."""
    b64_matches = re.findall(r"(?:[A-Za-z0-9+/]{4}){6,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?", text)
    for b64 in b64_matches:
        try:
            decoded = base64.b64decode(b64).decode("utf-8")
            if any(kw in decoded.lower() for kw in ["ignore", "override", "system", "grant", "bypass"]):
                return f"Decoded hidden payload: '{decoded}'"
        except Exception:
            continue
    return None


def scan_ingress_security(text: str) -> SecurityScanResult:
    """
    Evaluates incoming casework text for adversarial prompt injection,
    social engineering attacks, or policy evasion tactics.
    """
    if not text or not text.strip():
        return SecurityScanResult()

    matched_signatures = []
    highest_level = "CLEAN"
    primary_threat = None
    summary_reasons = []

    # 1. Rule Pattern Matching
    for rule in ADVERSARIAL_RULES:
        matches = re.findall(rule["pattern"], text)
        if matches:
            matched_signatures.append(rule["type"])
            summary_reasons.append(rule["summary"])
            if rule["level"] == "CRITICAL":
                highest_level = "CRITICAL"
                primary_threat = rule["type"]
            elif rule["level"] == "ELEVATED" and highest_level != "CRITICAL":
                highest_level = "ELEVATED"
                primary_threat = rule["type"]

    # 2. Obfuscation Check
    b64_threat = check_base64_obfuscation(text)
    if b64_threat:
        matched_signatures.append("OBFUSCATED_BASE64_PAYLOAD")
        summary_reasons.append(f"Encoded payload detected: {b64_threat}")
        highest_level = "CRITICAL"
        primary_threat = "OBFUSCATED_BASE64_PAYLOAD"

    if highest_level != "CLEAN":
        return SecurityScanResult(
            is_safe=False,
            threat_level=highest_level,
            threat_type=primary_threat,
            matched_signatures=matched_signatures,
            threat_summary=" | ".join(summary_reasons),
            remediation="Security firewall intercept: Block automated LLM reasoning and quarantine case for human investigator."
        )

    return SecurityScanResult(
        is_safe=True,
        threat_level="CLEAN",
        threat_type=None,
        matched_signatures=[],
        threat_summary="Ingress verification passed. Zero adversarial signatures detected.",
        remediation="Proceed with normal policy pipeline."
    )
