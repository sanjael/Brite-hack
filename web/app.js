/**
 * CALDER COUNTY DEPARTMENT OF HOUSEHOLD SERVICES
 * Automated Casework Assistant — Web Frontend Engine
 */

// --- GLOBAL APPLICATION STATE ---
const state = {
  runId: `RUN-${new Date().toISOString().replace(/[-:T]/g, "").slice(0, 15)}`,
  queue: [],
  currentIndex: 0,
  historyCache: {},
  currentResidentHistory: null,
  currentDecision: null,
  currentTriage: null,
  completedReferrals: [],
  approvedReferrals: [],
  rejectedReferrals: [],
  escalatedReferrals: [],
  handoffReferrals: [],
  failedReferrals: [],
  logs: [],
  autoStepping: false,
};

// --- WEB AUDIO CHIMES FOR MICRO-INTERACTIONS ---
const audioCtx = typeof AudioContext !== "undefined" ? new AudioContext() : null;

function playChime(type) {
  if (!audioCtx) return;
  if (audioCtx.state === "suspended") audioCtx.resume();

  try {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);

    const now = audioCtx.currentTime;
    if (type === "success") {
      osc.frequency.setValueAtTime(523.25, now); // C5
      osc.frequency.exponentialRampToValueAtTime(659.25, now + 0.1); // E5
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
      osc.start(now);
      osc.stop(now + 0.25);
    } else if (type === "gate") {
      osc.frequency.setValueAtTime(440, now); // A4
      osc.frequency.exponentialRampToValueAtTime(349.23, now + 0.15); // F4
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
      osc.start(now);
      osc.stop(now + 0.3);
    } else if (type === "complete") {
      [523.25, 659.25, 783.99, 1046.5].forEach((f, i) => {
        const o = audioCtx.createOscillator();
        const g = audioCtx.createGain();
        o.connect(g);
        g.connect(audioCtx.destination);
        o.frequency.value = f;
        g.gain.setValueAtTime(0.1, now + i * 0.08);
        g.gain.exponentialRampToValueAtTime(0.01, now + i * 0.08 + 0.3);
        o.start(now + i * 0.08);
        o.stop(now + i * 0.08 + 0.3);
      });
    }
  } catch (e) {
    // Audio synthesis not critical
  }
}

// --- DOM ELEMENTS ---
const elements = {
  headerRunId: document.getElementById("header-run-id"),
  themeToggle: document.getElementById("theme-toggle"),
  kpiTotal: document.getElementById("kpi-total"),
  kpiAutonomous: document.getElementById("kpi-autonomous"),
  kpiApproved: document.getElementById("kpi-approved"),
  kpiHandoffs: document.getElementById("kpi-handoffs"),
  kpiEscalated: document.getElementById("kpi-escalated"),
  queueProgressText: document.getElementById("queue-progress-text"),
  btnStartQueue: document.getElementById("btn-start-queue"),
  btnAutoRun: document.getElementById("btn-auto-run"),
  refIdVal: document.getElementById("ref-id-val"),
  residentRefVal: document.getElementById("resident-ref-val"),
  refSummaryVal: document.getElementById("ref-summary-val"),
  refActionVal: document.getElementById("ref-action-val"),
  referralUrgencyBadge: document.getElementById("referral-urgency-badge"),
  residentStatusBadge: document.getElementById("resident-status-badge"),
  residentDistrictVal: document.getElementById("resident-district-val"),
  residentAwardVal: document.getElementById("resident-award-val"),
  householdTbody: document.getElementById("household-tbody"),
  timelineEventsContainer: document.getElementById("timeline-events-container"),
  engineDynamicView: document.getElementById("engine-dynamic-view"),
  enginePolicyBadge: document.getElementById("engine-policy-badge"),
  aiSummaryText: document.getElementById("ai-summary-text"),
  aiRiskVal: document.getElementById("ai-risk-val"),
  aiActionVal: document.getElementById("ai-action-val"),
  queueSearch: document.getElementById("queue-search"),
  urgencyFilter: document.getElementById("urgency-filter"),
  queueTableBody: document.getElementById("queue-table-body"),
  sandboxActionInput: document.getElementById("sandbox-action-input"),
  btnTestPolicy: document.getElementById("btn-test-policy"),
  sandboxResult: document.getElementById("sandbox-result"),
  artifactsContainer: document.getElementById("artifacts-cards-container"),
  btnViewHandoffs: document.getElementById("btn-view-handoffs"),
  btnViewEscalations: document.getElementById("btn-view-escalations"),
  btnRefreshArtifacts: document.getElementById("btn-refresh-artifacts"),
  consoleLogsBox: document.getElementById("console-logs-box"),
  btnExportAuditJson: document.getElementById("btn-export-audit-json"),
  supervisorModal: document.getElementById("supervisor-modal"),
  modalRefId: document.getElementById("modal-ref-id"),
  modalResRef: document.getElementById("modal-res-ref"),
  modalActionName: document.getElementById("modal-action-name"),
  modalPolicyReason: document.getElementById("modal-policy-reason"),
  modalTokenPreview: document.getElementById("modal-token-preview"),
  btnModalApprove: document.getElementById("btn-modal-approve"),
  btnModalReject: document.getElementById("btn-modal-reject"),
};

// --- LOGGING UTILITY ---
function logConsole(msg) {
  const time = new Date().toLocaleTimeString();
  const entry = `[${time}] ${msg}`;
  state.logs.push(entry);
  if (elements.consoleLogsBox) {
    elements.consoleLogsBox.innerHTML = state.logs.slice(-20).join("<br>");
    elements.consoleLogsBox.scrollTop = elements.consoleLogsBox.scrollHeight;
  }
}

// --- INITIALIZE APPLICATION ---
async function initApp() {
  elements.headerRunId.textContent = state.runId;
  logConsole("Initializing Calder County DHS Caseworker Engine...");

  // Setup Theme
  elements.themeToggle.addEventListener("click", () => {
    document.body.classList.toggle("light-theme");
    elements.themeToggle.textContent = document.body.classList.contains("light-theme") ? "☀️" : "🌙";
  });

  // Setup Tabs
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      const tabId = btn.getAttribute("data-tab");
      document.getElementById(tabId).classList.add("active");
      if (tabId === "tab-artifacts") loadArtifacts();
    });
  });

  // Load Queue
  await loadQueueData();

  // Bind Buttons
  elements.btnStartQueue.addEventListener("click", startMorningQueue);
  elements.btnAutoRun.addEventListener("click", toggleAutoRun);
  elements.queueSearch.addEventListener("input", renderQueueTable);
  elements.urgencyFilter.addEventListener("change", renderQueueTable);
  elements.btnTestPolicy.addEventListener("click", testPolicySandbox);
  elements.btnViewHandoffs.addEventListener("click", () => loadArtifacts("handoffs"));
  elements.btnViewEscalations.addEventListener("click", () => loadArtifacts("escalations"));
  elements.btnRefreshArtifacts.addEventListener("click", () => loadArtifacts());
  elements.btnExportAuditJson.addEventListener("click", exportAuditJson);
  elements.btnModalApprove.addEventListener("click", handleModalApprove);
  elements.btnModalReject.addEventListener("click", handleModalReject);

  logConsole("System online. 12 referrals ready in overnight queue.");
}

// --- LOAD REFERRAL QUEUE ---
async function loadQueueData() {
  try {
    const res = await fetch("/api/queue");
    const data = await res.json();
    if (data.queue) {
      state.queue = data.queue;
      updateKpis();
      renderQueueTable();
      if (state.queue.length > 0) {
        displayReferral(0);
      }
    }
  } catch (err) {
    logConsole(`API error loading queue: ${err}`);
  }
}

// --- UPDATE KPIS ---
function updateKpis() {
  elements.kpiTotal.textContent = state.queue.length || 12;
  elements.kpiAutonomous.textContent = state.completedReferrals.length - state.approvedReferrals.length;
  elements.kpiApproved.textContent = state.approvedReferrals.length;
  elements.kpiHandoffs.textContent = state.handoffReferrals.length;
  elements.kpiEscalated.textContent = state.escalatedReferrals.length;
  elements.queueProgressText.textContent = `${Math.min(state.currentIndex, state.queue.length)} / ${state.queue.length}`;

  const total = state.queue.length || 12;
  const autoRate = (((state.completedReferrals.length - state.approvedReferrals.length) / (state.currentIndex || 1)) * 100).toFixed(1);
  const gateRate = ((state.approvedReferrals.length / (state.currentIndex || 1)) * 100).toFixed(1);
  const guardRate = (((state.handoffReferrals.length + state.escalatedReferrals.length) / (state.currentIndex || 1)) * 100).toFixed(1);

  document.getElementById("analytics-auto-rate").textContent = `${autoRate}%`;
  document.getElementById("analytics-gate-rate").textContent = `${gateRate}%`;
  document.getElementById("analytics-guard-rate").textContent = `${guardRate}%`;
}

// --- START / RESET QUEUE ---
function startMorningQueue() {
  state.currentIndex = 0;
  state.completedReferrals = [];
  state.approvedReferrals = [];
  state.rejectedReferrals = [];
  state.escalatedReferrals = [];
  state.handoffReferrals = [];
  state.failedReferrals = [];
  state.autoStepping = false;
  state.runId = `RUN-${new Date().toISOString().replace(/[-:T]/g, "").slice(0, 15)}`;
  elements.headerRunId.textContent = state.runId;

  logConsole("Morning sequence initialized with 12 referrals.");
  updateKpis();
  displayReferral(0);
}

// --- DISPLAY CURRENT REFERRAL ---
async function displayReferral(index) {
  if (!state.queue || index >= state.queue.length) {
    renderRunComplete();
    return;
  }

  const item = state.queue[index];
  state.currentIndex = index;
  updateKpis();

  // Set Stepper
  document.querySelectorAll(".step-node").forEach((s) => s.classList.remove("active", "completed"));
  document.getElementById("step-1").classList.add("completed");
  document.getElementById("step-2").classList.add("active");

  // Referral Info
  elements.refIdVal.textContent = item.referral_id;
  elements.residentRefVal.textContent = item.resident_ref;
  elements.refSummaryVal.textContent = item.summary;
  elements.refActionVal.textContent = item.requested_action;

  const isHigh = item.urgency.toLowerCase() === "high";
  elements.referralUrgencyBadge.textContent = `${item.urgency.toUpperCase()} URGENCY`;
  elements.referralUrgencyBadge.className = `badge-pill ${isHigh ? "badge-denied" : "badge-allowed"}`;

  // Fetch Resident History
  try {
    const res = await fetch(`/api/resident/${item.resident_ref}`);
    const hist = await res.json();
    state.currentResidentHistory = hist;

    document.getElementById("step-2").classList.add("completed");
    document.getElementById("step-3").classList.add("active");

    renderResidentHistory(hist);
    await evaluateCase(item, hist);
  } catch (err) {
    logConsole(`History fetch error for ${item.resident_ref}: ${err}`);
  }
}

// --- RENDER RESIDENT HISTORY ---
function renderResidentHistory(hist) {
  elements.residentStatusBadge.textContent = (hist.status || "ACTIVE").toUpperCase();
  elements.residentDistrictVal.textContent = hist.district || "Calder Central";
  elements.residentAwardVal.textContent = `£${Number(hist.award_monthly || 0).toFixed(2)}`;

  // Household Table
  elements.householdTbody.innerHTML = "";
  if (hist.household && hist.household.length > 0) {
    hist.household.forEach((m) => {
      const isMinor = m.is_minor || (m.age !== "UNKNOWN" && m.age !== null && Number(m.age) < 18);
      const minorBadge = isMinor
        ? '<span class="badge-minor">👶 MINOR (<18)</span>'
        : '<span style="color:var(--text-muted); font-size:0.75rem;">Adult</span>';

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-weight:600;">${m.name}</td>
        <td style="color:var(--text-secondary);">${m.relationship}</td>
        <td class="mono" style="font-size:0.8rem; color:var(--text-muted);">${m.date_of_birth || "N/A"}</td>
        <td style="font-weight:700;">${m.age !== undefined ? m.age : "N/A"}</td>
        <td>${minorBadge}</td>
      `;
      elements.householdTbody.appendChild(tr);
    });
  }

  // Events Timeline
  elements.timelineEventsContainer.innerHTML = "";
  if (hist.events && hist.events.length > 0) {
    hist.events.forEach((ev) => {
      const div = document.createElement("div");
      div.className = "timeline-event";
      div.innerHTML = `
        <div class="timeline-date">${ev.date}</div>
        <div class="timeline-name">${ev.type}</div>
        <div class="timeline-desc">${ev.detail}</div>
      `;
      elements.timelineEventsContainer.appendChild(div);
    });
  }
}

// --- EVALUATE POLICY & SAFEGUARDS ---
async function evaluateCase(item, hist) {
  // 1. Check ACA-2026/2 Minor Policy (§3.9)
  const minorRes = await fetch("/api/evaluate_household", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ household: hist.household, action: item.requested_action }),
  });
  const minorData = await minorRes.json();

  if (minorData.has_minor) {
    // ACA-2026/2 MINOR SAFEGUARD ACTIVE
    document.getElementById("step-3").classList.add("completed");
    document.getElementById("step-5").classList.add("active");

    elements.enginePolicyBadge.textContent = "SECTION 3.9 RESTRICTION";
    elements.enginePolicyBadge.className = "badge-pill badge-handoff";

    elements.aiSummaryText.textContent = "🛑 [AI TRIAGE GENERATION RESTRICTED UNDER ACA-2026/2 SECTION 3.9 - MINOR IN HOUSEHOLD]";
    elements.aiRiskVal.textContent = "SAFEGUARD MANDATE";
    elements.aiActionVal.textContent = "Caseworker Handoff";

    elements.engineDynamicView.innerHTML = `
      <div class="alert-box info">
        <div class="alert-title">🛡️ ACA-2026/2 SAFEGUARD: MINOR IN HOUSEHOLD</div>
        <div class="alert-desc">
          Household contains a resident under 18 years of age. Under <b>Policy ACA-2026/2 Section 3.9</b>, the AI model is <b>structurally prohibited</b> from drafting triage notes.
          <div style="margin-top:8px; font-weight:600;">Reason: ${minorData.decision ? minorData.decision.reason : "Minor dependent present"}</div>
        </div>
      </div>

      <div style="background:var(--bg-surface-elevated); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:16px; margin-bottom:16px;">
        <div style="font-size:0.75rem; font-weight:700; color:var(--text-secondary); text-transform:uppercase; margin-bottom:8px;">Handoff Dossier Generated:</div>
        <div style="font-size:0.85rem; color:var(--accent-success);">✓ Referral Intake Registered</div>
        <div style="font-size:0.85rem; color:var(--accent-success);">✓ Resident History Reconciled</div>
        <div style="font-size:0.85rem; color:var(--accent-success);">✓ Minor Dependent Safeguard Verified</div>
        <div style="font-size:0.85rem; color:var(--accent-danger); font-weight:700;">✗ AI Triage Draft: RESTRICTED BY LAW</div>
      </div>

      <button class="btn btn-primary btn-full" id="btn-next-handoff">➡️ Create Handoff Artifact &amp; Continue</button>
    `;

    // Persist Handoff via API
    await fetch("/api/create_handoff", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: state.runId,
        current_referral: item,
        resident_history: hist,
        policy_decision: minorData.decision,
      }),
    });

    if (!state.handoffReferrals.includes(item.referral_id)) {
      state.handoffReferrals.push(item.referral_id);
    }
    updateKpis();

    document.getElementById("btn-next-handoff").addEventListener("click", () => {
      playChime("success");
      logConsole(`🛡️ Caseworker Handoff generated for ${item.referral_id} (ACA-2026/2 §3.9)`);
      displayReferral(state.currentIndex + 1);
    });

    if (state.autoStepping) {
      setTimeout(() => {
        document.getElementById("btn-next-handoff")?.click();
      }, 700);
    }

    return;
  }

  // 2. Safe Adult Household -> Generate AI Triage Reasoning
  document.getElementById("step-3").classList.add("completed");
  document.getElementById("step-4").classList.add("active");

  const triageRes = await fetch("/api/triage", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ referral: item, history: hist }),
  });
  const triageData = await triageRes.json();
  state.currentTriage = triageData.triage_note;

  elements.aiSummaryText.textContent = state.currentTriage.situation_summary;
  elements.aiRiskVal.textContent = state.currentTriage.risk_level.toUpperCase();
  elements.aiActionVal.textContent = state.currentTriage.recommended_action;

  document.getElementById("step-4").classList.add("completed");
  document.getElementById("step-5").classList.add("active");

  // 3. Evaluate Requested Action Policy (ACA-2026/1)
  const policyRes = await fetch("/api/evaluate_action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: item.requested_action }),
  });
  const policyData = await policyRes.json();
  state.currentDecision = policyData;

  // SECTION 2: AUTONOMOUS ACTION
  if (policyData.decision === "ALLOWED") {
    elements.enginePolicyBadge.textContent = `SECTION ${policyData.policy_section} ALLOWED`;
    elements.enginePolicyBadge.className = "badge-pill badge-allowed";

    elements.engineDynamicView.innerHTML = `
      <div class="alert-box success">
        <div class="alert-title">⚡ POLICY RESULT: AUTONOMOUS EXECUTION</div>
        <div class="alert-desc">
          <b>Policy Rule ${policyData.policy_rule}:</b> ${policyData.reason}
        </div>
      </div>
      <div style="background:var(--bg-surface-elevated); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:14px; margin-bottom:16px;">
        <div style="font-size:0.85rem; color:var(--accent-success); font-weight:600;">✓ Action verified within caseworker automated authority boundary.</div>
      </div>
      <button class="btn btn-success btn-full" id="btn-next-execute">✓ Execute Action &amp; Continue</button>
    `;

    if (!state.completedReferrals.includes(item.referral_id)) {
      state.completedReferrals.push(item.referral_id);
    }
    updateKpis();

    document.getElementById("btn-next-execute").addEventListener("click", () => {
      playChime("success");
      logConsole(`✓ Autonomously executed ${item.referral_id} (${item.requested_action})`);
      displayReferral(state.currentIndex + 1);
    });

    if (state.autoStepping) {
      setTimeout(() => {
        document.getElementById("btn-next-execute")?.click();
      }, 600);
    }
  }

  // SECTION 4: EXPLICITLY DENIED & ESCALATED
  else if (policyData.decision === "DENIED") {
    elements.enginePolicyBadge.textContent = `SECTION ${policyData.policy_section} PROHIBITED`;
    elements.enginePolicyBadge.className = "badge-pill badge-denied";

    elements.engineDynamicView.innerHTML = `
      <div class="alert-box danger">
        <div class="alert-title">⛔ CRITICAL SECURITY BOUNDARY BREACH REFUSED</div>
        <div class="alert-desc">
          <b>Policy Rule ${policyData.policy_rule}:</b> ${policyData.reason}
        </div>
      </div>
      <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:16px;">
        Under Policy Section 3.2, 3.7 &amp; 4.1, automated suspension of welfare assistance is strictly forbidden. Formal escalation dossier generated.
      </div>
      <button class="btn btn-danger btn-full" id="btn-next-escalate">⚠️ Confirm Escalation Dossier &amp; Continue</button>
    `;

    // Persist Escalation
    await fetch("/api/escalate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: state.runId,
        current_referral: item,
        policy_decision: policyData,
        triage_note: state.currentTriage,
      }),
    });

    if (!state.escalatedReferrals.includes(item.referral_id)) {
      state.escalatedReferrals.push(item.referral_id);
    }
    updateKpis();

    document.getElementById("btn-next-escalate").addEventListener("click", () => {
      playChime("gate");
      logConsole(`⚠️ Out-of-authority action refused & escalated: ${item.referral_id}`);
      displayReferral(state.currentIndex + 1);
    });

    if (state.autoStepping) {
      setTimeout(() => {
        document.getElementById("btn-next-escalate")?.click();
      }, 700);
    }
  }

  // SECTION 3: SUPERVISOR APPROVAL REQUIRED GATE
  else if (policyData.decision === "APPROVAL_REQUIRED") {
    elements.enginePolicyBadge.textContent = `SECTION ${policyData.policy_section} PROTECTED`;
    elements.enginePolicyBadge.className = "badge-pill badge-approval";

    elements.engineDynamicView.innerHTML = `
      <div class="alert-box warning">
        <div class="alert-title">🔒 HARD APPROVAL GATE ACTIVE</div>
        <div class="alert-desc">
          <b>*** NO ACTION HAS BEEN EXECUTED ***</b><br>
          Action modifies financial benefit entitlement or payment credentials. Requires cryptographic HMAC authorization from human supervisor.
        </div>
      </div>
      <div style="margin-bottom:16px; font-size:0.85rem; color:var(--text-secondary);">
        <b>Policy Reason:</b> ${policyData.reason}
      </div>
      <button class="btn btn-primary btn-full" id="btn-open-gate-modal">🛡️ Open Cryptographic Supervisor Gate</button>
    `;

    document.getElementById("btn-open-gate-modal").addEventListener("click", () => {
      openSupervisorModal(item, policyData);
    });

    // Pause auto-stepping for supervisor gate
    if (state.autoStepping) {
      state.autoStepping = false;
      elements.btnAutoRun.textContent = "🤖 Auto-Process Safe Cases";
      openSupervisorModal(item, policyData);
    }
  }
}

// --- OPEN SUPERVISOR MODAL ---
function openSupervisorModal(item, policyData) {
  playChime("gate");
  elements.modalRefId.textContent = item.referral_id;
  elements.modalResRef.textContent = item.resident_ref;
  elements.modalActionName.textContent = item.requested_action;
  elements.modalPolicyReason.textContent = policyData.reason;
  elements.modalTokenPreview.textContent = `HMAC-SHA256: [PENDING_SUPERVISOR_SIGNATURE] TARGET:${item.referral_id} ACTION:${item.requested_action}`;
  elements.supervisorModal.classList.add("active");
}

// --- HANDLE SUPERVISOR APPROVE ---
async function handleModalApprove() {
  const item = state.queue[state.currentIndex];
  const tokenRes = await fetch("/api/generate_token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ referral_id: item.referral_id, action: item.requested_action, run_id: state.runId }),
  });
  const token = await tokenRes.json();

  await fetch("/api/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      run_id: state.runId,
      current_referral: item,
      policy_decision: state.currentDecision,
      approval_token: token,
    }),
  });

  if (!state.completedReferrals.includes(item.referral_id)) state.completedReferrals.push(item.referral_id);
  if (!state.approvedReferrals.includes(item.referral_id)) state.approvedReferrals.push(item.referral_id);

  elements.supervisorModal.classList.remove("active");
  playChime("success");
  logConsole(`✓ Supervisor HMAC Signed & Executed: ${item.referral_id} (${token.token_id})`);
  displayReferral(state.currentIndex + 1);
}

// --- HANDLE SUPERVISOR REJECT ---
async function handleModalReject() {
  const item = state.queue[state.currentIndex];
  await fetch("/api/escalate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      run_id: state.runId,
      current_referral: item,
      policy_decision: state.currentDecision,
      triage_note: state.currentTriage,
    }),
  });

  if (!state.escalatedReferrals.includes(item.referral_id)) state.escalatedReferrals.push(item.referral_id);
  if (!state.rejectedReferrals.includes(item.referral_id)) state.rejectedReferrals.push(item.referral_id);

  elements.supervisorModal.classList.remove("active");
  playChime("gate");
  logConsole(`✖ Supervisor Rejected & Escalated: ${item.referral_id}`);
  displayReferral(state.currentIndex + 1);
}

// --- TOGGLE AUTO RUN ---
function toggleAutoRun() {
  state.autoStepping = !state.autoStepping;
  elements.btnAutoRun.textContent = state.autoStepping ? "⏸️ Pause Auto-Processing" : "🤖 Auto-Process Safe Cases";
  if (state.autoStepping) {
    logConsole("Auto-processing started for autonomous and handoff referrals.");
    const curItem = state.queue[state.currentIndex];
    if (curItem) displayReferral(state.currentIndex);
  }
}

// --- RENDER RUN COMPLETE ---
async function renderRunComplete() {
  playChime("complete");
  document.getElementById("card-execution-engine").innerHTML = `
    <div style="text-align:center; padding:30px 20px;">
      <div style="font-size:3rem; margin-bottom:10px;">🎉</div>
      <h2 style="color:var(--accent-success); margin-bottom:8px;">CASEWORKER MORNING RUN COMPLETE</h2>
      <p style="color:var(--text-secondary); max-width:540px; margin:0 auto 16px auto; font-size:0.95rem;">
        All 12 overnight referrals processed under Policy ACA-2026/1 &amp; ACA-2026/2 with deterministic security guardrails.
      </p>
      <div style="display:inline-flex; gap:16px; background:var(--bg-surface-elevated); padding:10px 20px; border-radius:var(--radius-md); font-family:var(--font-mono); font-size:0.85rem;">
        <span>✓ Completed: <b>${state.completedReferrals.length}</b></span>
        <span>🔒 Approved: <b>${state.approvedReferrals.length}</b></span>
        <span>🛡️ Handoffs: <b>${state.handoffReferrals.length}</b></span>
        <span>⚠️ Escalated: <b>${state.escalatedReferrals.length}</b></span>
      </div>
    </div>
  `;

  // Persist Run Summary via API
  await fetch("/api/save_run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      run_id: state.runId,
      total: state.queue.length,
      completed: state.completedReferrals.length,
      approved: state.approvedReferrals.length,
      rejected: state.rejectedReferrals.length,
      escalated: state.escalatedReferrals.length,
      handoffs: state.handoffReferrals.length,
      failed: state.failedReferrals.length,
      timestamp: new Date().toISOString(),
    }),
  });

  logConsole("Morning referral audit trace saved to artifacts/runs/.");
}

// --- RENDER QUEUE TABLE (TAB 2) ---
function renderQueueTable() {
  const query = (elements.queueSearch.value || "").toLowerCase();
  const filterUrgency = elements.urgencyFilter.value;

  elements.queueTableBody.innerHTML = "";
  state.queue.forEach((item, i) => {
    if (filterUrgency !== "ALL" && item.urgency !== filterUrgency) return;
    if (
      query &&
      !item.referral_id.toLowerCase().includes(query) &&
      !item.resident_ref.toLowerCase().includes(query) &&
      !item.requested_action.toLowerCase().includes(query) &&
      !item.summary.toLowerCase().includes(query)
    ) {
      return;
    }

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="mono" style="font-weight:700; color:var(--accent-primary);">${item.referral_id}</td>
      <td class="mono">${item.resident_ref}</td>
      <td>${item.source}</td>
      <td class="mono" style="font-weight:600;">${item.requested_action}</td>
      <td><span class="badge-pill ${item.urgency.toLowerCase() === "high" ? "badge-denied" : "badge-allowed"}">${item.urgency}</span></td>
      <td style="max-width:320px; font-size:0.82rem; color:var(--text-secondary);">${item.summary}</td>
      <td><button class="btn btn-secondary" style="padding:4px 10px; font-size:0.75rem;" onclick="jumpToCase(${i})">Inspect</button></td>
    `;
    elements.queueTableBody.appendChild(tr);
  });
}

window.jumpToCase = function (index) {
  document.querySelector('[data-tab="tab-workspace"]').click();
  displayReferral(index);
};

// --- TEST POLICY SANDBOX (TAB 3) ---
async function testPolicySandbox() {
  const action = elements.sandboxActionInput.value.trim();
  if (!action) return;

  const res = await fetch("/api/evaluate_action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  const data = await res.json();

  elements.sandboxResult.style.display = "block";
  if (data.decision === "ALLOWED") {
    elements.sandboxResult.style.background = "var(--accent-success-bg)";
    elements.sandboxResult.style.border = "1px solid var(--accent-success-border)";
    elements.sandboxResult.style.color = "var(--accent-success)";
    elements.sandboxResult.innerHTML = `<b>✓ ALLOWED (Section ${data.policy_section} - Rule ${data.policy_rule}):</b> ${data.reason}`;
  } else if (data.decision === "APPROVAL_REQUIRED") {
    elements.sandboxResult.style.background = "var(--accent-warning-bg)";
    elements.sandboxResult.style.border = "1px solid var(--accent-warning-border)";
    elements.sandboxResult.style.color = "var(--accent-warning)";
    elements.sandboxResult.innerHTML = `<b>🔒 SUPERVISOR APPROVAL REQUIRED (Section ${data.policy_section} - Rule ${data.policy_rule}):</b> ${data.reason}`;
  } else {
    elements.sandboxResult.style.background = "var(--accent-danger-bg)";
    elements.sandboxResult.style.border = "1px solid var(--accent-danger-border)";
    elements.sandboxResult.style.color = "var(--accent-danger)";
    elements.sandboxResult.innerHTML = `<b>⛔ PROHIBITED / ESCALATE (Section ${data.policy_section} - Rule ${data.policy_rule}):</b> ${data.reason}`;
  }
}

// --- LOAD ARTIFACTS (TAB 4) ---
async function loadArtifacts(filterType = "handoffs") {
  try {
    const res = await fetch("/api/artifacts");
    const data = await res.json();
    elements.artifactsContainer.innerHTML = "";

    const items = filterType === "handoffs" ? data.handoffs : data.escalations;
    if (!items || items.length === 0) {
      elements.artifactsContainer.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted);">No ${filterType} generated yet in current run.</div>`;
      return;
    }

    items.forEach((art) => {
      const card = document.createElement("div");
      card.style.cssText = "background:var(--bg-surface-elevated); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:16px; margin-bottom:14px;";
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
          <div style="font-weight:700; color:var(--accent-primary);" class="mono">📄 ${art.referral_id || "Artifact"} (Resident: ${art.resident_ref})</div>
          <span class="badge-pill ${filterType === "handoffs" ? "badge-handoff" : "badge-denied"}">${art.status}</span>
        </div>
        <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:8px;">${art.reason}</div>
        <pre style="background:var(--bg-app); padding:12px; border-radius:var(--radius-sm); font-size:0.75rem; color:var(--text-primary); max-height:160px; overflow-y:auto;">${JSON.stringify(art, null, 2)}</pre>
      `;
      elements.artifactsContainer.appendChild(card);
    });
  } catch (err) {
    elements.artifactsContainer.innerHTML = `<div style="color:var(--accent-danger);">Error loading artifacts: ${err}</div>`;
  }
}

// --- EXPORT AUDIT JSON (TAB 5) ---
function exportAuditJson() {
  const auditReport = {
    run_id: state.runId,
    timestamp: new Date().toISOString(),
    total_referrals: state.queue.length,
    completed: state.completedReferrals,
    approved: state.approvedReferrals,
    rejected: state.rejectedReferrals,
    escalated: state.escalatedReferrals,
    handoffs: state.handoffReferrals,
    logs: state.logs,
  };

  const blob = new Blob([JSON.stringify(auditReport, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `AUDIT_${state.runId}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// --- BOOTSTRAP ---
document.addEventListener("DOMContentLoaded", initApp);
