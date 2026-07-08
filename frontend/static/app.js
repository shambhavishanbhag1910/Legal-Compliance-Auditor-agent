const state = {
  file: null,
  document: null,
  audit: null,
  activeFilter: "all",
};

const el = (id) => document.getElementById(id);

const fileInput = el("fileInput");
const uploadZone = el("uploadZone");
const runAuditBtn = el("runAuditBtn");
const welcomePanel = el("welcomePanel");
const progressPanel = el("progressPanel");
const results = el("results");
const errorPanel = el("errorPanel");

function pct(value) {
  const n = Number(value ?? 0);
  return `${Math.round(n * 100)}%`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("Health check failed");
    const data = await response.json();

    document.querySelector(".system-dot").classList.add("good");
    el("systemStatus").textContent = "API connected";
    el("systemDetail").textContent =
      `${data.storage_backend ?? "local"} storage · model ready`;
  } catch (error) {
    document.querySelector(".system-dot").classList.add("bad");
    el("systemStatus").textContent = "API unavailable";
    el("systemDetail").textContent = "Start FastAPI on port 8000";
  }
}

function setFile(file) {
  if (!file) return;
  state.file = file;
  el("fileName").textContent = file.name;
  runAuditBtn.disabled = false;
}

fileInput.addEventListener("change", (event) => {
  setFile(event.target.files[0]);
});

["dragenter", "dragover"].forEach((name) => {
  uploadZone.addEventListener(name, (event) => {
    event.preventDefault();
    uploadZone.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((name) => {
  uploadZone.addEventListener(name, (event) => {
    event.preventDefault();
    uploadZone.classList.remove("dragging");
  });
});

uploadZone.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  setFile(file);
});

function showOnly(panel) {
  [welcomePanel, progressPanel, results, errorPanel].forEach((item) => {
    item.classList.add("hidden");
  });
  panel.classList.remove("hidden");
}

function updateProgress(stage, percent, title, message) {
  const order = ["upload", "evidence", "consensus", "judge"];
  const current = order.indexOf(stage);

  document.querySelectorAll(".stage").forEach((node) => {
    const index = order.indexOf(node.dataset.stage);
    node.classList.toggle("active", index === current);
    node.classList.toggle("complete", index < current);
  });

  el("progressBar").style.width = `${percent}%`;
  el("progressTitle").textContent = title;
  el("progressMessage").textContent = message;
}

function simulateLongStage() {
  const sequence = [
    [2500, "evidence", 44, "Evidence agent is searching the document and using tools..."],
    [9000, "consensus", 69, "Generating independent audit candidates and resolving rule-level consensus..."],
    [16000, "judge", 88, "Independent judge is checking grounding, completeness, and hallucination..."],
  ];

  return sequence.map(([delay, stage, percent, message]) =>
    setTimeout(() => {
      updateProgress(stage, percent, stage[0].toUpperCase() + stage.slice(1), message);
    }, delay)
  );
}

async function uploadDocument() {
  const form = new FormData();
  form.append("file", state.file);

  const response = await fetch("/documents", {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Document upload failed (${response.status}): ${body}`);
  }

  return response.json();
}

async function createAudit(documentId) {
  const response = await fetch("/audits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_id: documentId,
      framework: el("framework").value,
      runs: Number(el("runs").value),
    }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Audit failed (${response.status}): ${body}`);
  }

  return response.json();
}

runAuditBtn.addEventListener("click", async () => {
  if (!state.file) return;

  runAuditBtn.disabled = true;
  showOnly(progressPanel);
  updateProgress("upload", 12, "Document ingestion", "Uploading and parsing the source document...");
  const timers = [];

  try {
    state.document = await uploadDocument();

    updateProgress(
      "evidence",
      34,
      "Evidence collection",
      "Evidence agent is selecting search tools and collecting source-grounded chunks..."
    );

    timers.push(...simulateLongStage());

    state.audit = await createAudit(state.document.document_id);

    timers.forEach(clearTimeout);
    updateProgress("judge", 100, "Audit complete", "Rendering the final validated assessment...");
    renderAudit(state.audit);

    setTimeout(() => showOnly(results), 350);
  } catch (error) {
    timers.forEach(clearTimeout);
    showError(error);
  } finally {
    runAuditBtn.disabled = false;
  }
});

function renderAudit(audit) {
  const report = audit.report;
  const judge = audit.judge;

  el("resultTitle").textContent =
    `${report.framework[0].toUpperCase() + report.framework.slice(1)} compliance assessment`;
  el("executiveSummary").textContent = report.executive_summary;

  el("riskValue").textContent = report.overall_risk;
  const riskBadge = el("riskBadge");
  riskBadge.style.background =
    report.overall_risk === "low" ? "var(--good-soft)" :
    ["high", "critical"].includes(report.overall_risk) ? "var(--bad-soft)" :
    "var(--warn-soft)";
  riskBadge.style.color =
    report.overall_risk === "low" ? "var(--good)" :
    ["high", "critical"].includes(report.overall_risk) ? "var(--bad)" :
    "var(--warn)";

  el("consensusMetric").textContent = pct(audit.consensus_agreement);
  el("faithfulnessMetric").textContent = pct(judge.faithfulness);
  el("completenessMetric").textContent = pct(judge.completeness);
  el("hallucinationMetric").textContent = pct(judge.hallucination_rate);

  el("judgeComments").textContent = judge.comments;
  el("unsupportedCount").textContent = judge.unsupported_finding_ids.length;
  el("fabricatedCount").textContent = judge.fabricated_claims.length;

  state.activeFilter = "all";
  document.querySelectorAll(".filter").forEach((button) => {
    button.classList.toggle("active", button.dataset.filter === "all");
  });

  renderFindings(report.findings);
  renderTrace(audit.tool_trace);
  renderLimitations(report.limitations);
}

function renderFindings(findings) {
  const filtered = state.activeFilter === "all"
    ? findings
    : findings.filter((f) => f.status === state.activeFilter);

  const container = el("findingsList");

  if (!filtered.length) {
    container.innerHTML = `<div class="detail-box"><p>No findings in this category.</p></div>`;
    return;
  }

  container.innerHTML = filtered.map((finding) => {
    const evidence = finding.evidence?.[0];
    return `
      <article class="finding-card">
        <div class="finding-main">
          <div class="finding-top">
            <div class="finding-title-row">
              <span class="rule-id">${escapeHtml(finding.rule_id)}</span>
              <span class="finding-name">${escapeHtml(finding.rule_name)}</span>
            </div>
            <div class="badge-row">
              <span class="status-badge status-${escapeHtml(finding.status)}">
                ${escapeHtml(finding.status.replaceAll("_", " "))}
              </span>
              <span class="severity-badge severity-${escapeHtml(finding.severity)}">
                ${escapeHtml(finding.severity)}
              </span>
            </div>
          </div>
          <p class="finding-summary">${escapeHtml(finding.summary)}</p>
        </div>
        <div class="finding-detail">
          <div class="detail-box">
            <span>Evidence</span>
            ${
              evidence
                ? `<p class="evidence-quote">“${escapeHtml(evidence.quote)}”<br><small>${escapeHtml(evidence.chunk_id)}</small></p>`
                : `<p>No direct evidence attached.</p>`
            }
          </div>
          <div class="detail-box">
            <span>Remediation</span>
            <p>${escapeHtml(finding.remediation)}</p>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

el("findingFilters").addEventListener("click", (event) => {
  const button = event.target.closest(".filter");
  if (!button || !state.audit) return;

  state.activeFilter = button.dataset.filter;
  document.querySelectorAll(".filter").forEach((node) => {
    node.classList.toggle("active", node === button);
  });

  renderFindings(state.audit.report.findings);
});

function renderTrace(trace) {
  el("traceCount").textContent = `${trace.length} calls`;
  el("traceList").innerHTML = trace.length
    ? trace.map((item) => `
        <div class="trace-item">
          <strong>${escapeHtml(item.tool_name)}</strong>
          <p>${escapeHtml(item.purpose)}</p>
        </div>
      `).join("")
    : `<div class="detail-box"><p>No tool calls recorded.</p></div>`;
}

function renderLimitations(limitations) {
  el("limitationsList").innerHTML = limitations.length
    ? limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
    : "<li>No additional limitations reported.</li>";
}

function showError(error) {
  showOnly(errorPanel);
  el("errorMessage").textContent = error?.message ?? String(error);
}

el("retryBtn").addEventListener("click", () => {
  showOnly(welcomePanel);
});

checkHealth();
