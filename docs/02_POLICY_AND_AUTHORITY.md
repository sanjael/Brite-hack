# 02 — Policy and Authority Model

This document explains Policy Reference **ACA-2026/1** from a legal and governance perspective, independent of the Python code implementation.

---

## 1. Governance Principles
Calder County Department of Household Services is accountable for every decision affecting resident benefit awards. Policy ACA-2026/1 establishes a strict boundary between:
1. **Autonomous Operations** (Administrative intake, information retrieval, drafting notes, flagging).
2. **Supervised Operations** (Modifying awards, updating payment bank details, changing eligibility).
3. **Forbidden / Escalation Operations** (Suspending awards or alleging fraud without prior supervisor authorization).

---

## 2. Policy Rule Classification Matrix

### A. Section 2: Permitted Without Approval (`ALLOWED`)
* **2.1 / 2.5 — Record intake / Address updates**: E.g., `RF-2026-0413` ("Record change of address"). Updating resident address records requested directly by the resident.
* **2.4 — Draft Triage & Explanatory Notes**: E.g., `RF-2026-0417` ("Draft explanatory note") and `RF-2026-0422` ("Draft triage note for supervisor"). Drafting notes has no effect on the case until adopted by a human caseworker.
* **2.2 / 2.4 — Household Composition Review**: E.g., `RF-2026-0416` & `RF-2026-0421` ("Review household composition"). Querying household members and drafting notes is permitted. (Any resulting change to award amounts requires approval under 3.1).
* **2.6 — Flag for Human Attention**: E.g., `RF-2026-0420` ("Flag for contact attempt"). Flagging returned correspondence or unconfirmed whereabouts for human follow-up.

### B. Section 3: Requires Supervisor Approval (`APPROVAL_REQUIRED`)
* **3.1 — Award & Entitlement Changes**: E.g., `RF-2026-0412`, `RF-2026-0414`, `RF-2026-0418` ("Review award") and `RF-2026-0419` ("Record income change"). Recalculating award amounts affects resident entitlements.
* **3.4 — Payment Detail Changes**: E.g., `RF-2026-0423` ("Update payment details"). Changing bank account numbers or payment methods strictly requires prior supervisor approval.

### C. Section 3 / 4: Forbidden & Escalated (`DENIED`)
* **3.2 / 3.7 / 4.1 — Award Suspension & Fraud Assertions**: E.g., `RF-2026-0415` ("Suspend assistance pending investigation").
  * Section 3.2 prohibits automated award suspension.
  * Section 3.7 prohibits asserting findings of fact regarding fraud or misrepresentation.
  * Section 4.1 mandates immediate refusal and escalation to a supervisor.

### D. Section 6.1: Ambiguity Default Rule
* **Rule 6.1**: *"Where it is unclear whether an action falls within section 3, it is to be treated as though it does."*
* Any unknown, ambiguous, unlisted, or prompt-injected action string **must** default to `APPROVAL_REQUIRED` / `ESCALATION`.

---

## Related Documentation
* For how this policy is converted into machine-readable JSON rules, see [07_POLICY_ENGINE.md](07_POLICY_ENGINE.md).
* For human approval gate execution, see [08_APPROVAL_AND_HUMAN_GATE.md](08_APPROVAL_AND_HUMAN_GATE.md).
