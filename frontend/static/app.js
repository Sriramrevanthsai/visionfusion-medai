localStorage.removeItem("vf_token");
localStorage.removeItem("vf_user");

let token = "";
let currentUser = null;
let authMode = "login";

const authPanel = document.querySelector("#authPanel");
const workspace = document.querySelector("#workspace");
const authForm = document.querySelector("#authForm");
const authStatus = document.querySelector("#authStatus");
const caseForm = document.querySelector("#caseForm");
const caseStatus = document.querySelector("#caseStatus");
const resultCard = document.querySelector("#resultCard");
const caseList = document.querySelector("#caseList");
const adminPanel = document.querySelector("#adminPanel");
const adminUserForm = document.querySelector("#adminUserForm");
const adminStatus = document.querySelector("#adminStatus");
const userList = document.querySelector("#userList");
const modeSelect = document.querySelector("[name='mode']");

document.querySelector("#loginTab").addEventListener("click", () => setAuthMode("login"));
document.querySelector("#registerTab").addEventListener("click", () => setAuthMode("register"));
document.querySelector("#demoBtn").addEventListener("click", useDemo);
document.querySelector("#demoAdminBtn").addEventListener("click", useDemoAdmin);
document.querySelector("#refreshCases").addEventListener("click", loadCases);
document.querySelector("#refreshUsers").addEventListener("click", loadUsers);
document.querySelector("#caseType").addEventListener("change", updateWorkflowFields);
document.querySelector("#logoutBtn").addEventListener("click", logout);

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authStatus.textContent = "Checking credentials...";
  const body = new FormData(authForm);
  if (authMode === "login") body.delete("name");
  const response = await fetch(`/api/auth/${authMode}`, { method: "POST", body });
  const data = await response.json();
  if (!response.ok) {
    authStatus.textContent = data.detail || "Authentication failed";
    return;
  }
  saveSession(data);
});

caseForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  caseStatus.textContent = "Running MCP tools across image, voice, and text...";
  const body = new FormData(caseForm);
  body.append("token", token);
  const response = await fetch("/api/cases/analyze", { method: "POST", body });
  const data = await response.json();
  if (!response.ok) {
    caseStatus.textContent = data.detail || "Case analysis failed";
    return;
  }
  caseStatus.textContent = "Insight generated.";
  renderResult(data);
  loadCases();
});

adminUserForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  adminStatus.textContent = "Creating user...";
  const body = new FormData(adminUserForm);
  body.append("token", token);
  const response = await fetch("/api/admin/users", { method: "POST", body });
  const data = await response.json();
  if (!response.ok) {
    adminStatus.textContent = data.detail || "User creation failed";
    return;
  }
  adminUserForm.reset();
  adminStatus.textContent = `${data.name} created as ${data.role}.`;
  loadUsers();
});

function setAuthMode(mode) {
  authMode = mode;
  document.querySelector("#loginTab").classList.toggle("active", mode === "login");
  document.querySelector("#registerTab").classList.toggle("active", mode === "register");
  document.querySelectorAll(".register-only").forEach((item) => item.classList.toggle("hidden", mode !== "register"));
  authStatus.textContent = mode === "register" ? "Patients can self-register. Doctors and admins are created by admins." : "";
}

async function useDemo() {
  authStatus.textContent = "Opening demo workspace...";
  const response = await fetch("/api/demo-user");
  saveSession(await response.json());
}

async function useDemoAdmin() {
  authStatus.textContent = "Opening admin workspace...";
  const response = await fetch("/api/demo-admin");
  saveSession(await response.json());
}

function saveSession(data) {
  token = data.token;
  currentUser = data.user;
  showWorkspace();
}

function showWorkspace() {
  authPanel.classList.add("hidden");
  workspace.classList.remove("hidden");
  document.querySelector("#userChip").textContent = `${currentUser.name} | ${currentUser.role}`;
  applyRoleView();
  loadCases();
  if (currentUser.role === "admin") loadUsers();
}

function applyRoleView() {
  const isPatient = currentUser.role === "patient";
  const isAdmin = currentUser.role === "admin";
  modeSelect.value = isPatient ? "patient" : "doctor";
  modeSelect.disabled = isPatient;
  adminPanel.classList.toggle("hidden", !isAdmin);
}

async function loadCases() {
  if (!token) return;
  const response = await fetch(`/api/cases?token=${encodeURIComponent(token)}`);
  const cases = await response.json();
  caseList.innerHTML = cases.length ? "" : "<p class='status'>No cases yet. Generate your first insight above.</p>";
  cases.forEach((item) => {
    const node = document.createElement("article");
    node.className = "case-item";
    node.innerHTML = `
      <div>
        <strong>${item.patient_name} - ${item.analysis.risk_label}</strong>
        <p>${item.id} | ${new Date(item.created_at).toLocaleString()} | ${item.mode} mode</p>
      </div>
      <button class="ghost-btn compact" data-report="${item.id}">Report</button>
    `;
    node.querySelector("button").addEventListener("click", () => downloadReport(item.id));
    caseList.appendChild(node);
  });
}

async function loadUsers() {
  if (!token || currentUser.role !== "admin") return;
  const response = await fetch(`/api/admin/users?token=${encodeURIComponent(token)}`);
  const users = await response.json();
  if (!response.ok) {
    adminStatus.textContent = users.detail || "Could not load users";
    return;
  }
  userList.innerHTML = users.length ? "" : "<p class='status'>No users found.</p>";
  users.forEach((item) => {
    const node = document.createElement("article");
    node.className = "case-item user-item";
    const canDelete = item.email !== currentUser.email;
    node.innerHTML = `
      <div>
        <strong>${item.name} - ${item.role}</strong>
        <p>${item.email}</p>
      </div>
      ${canDelete ? `<button class="ghost-btn compact danger-btn" data-user="${item.email}">Delete</button>` : "<span class='status'>Current admin</span>"}
    `;
    const button = node.querySelector("button");
    if (button) button.addEventListener("click", () => deleteUser(item.email));
    userList.appendChild(node);
  });
}

async function deleteUser(email) {
  adminStatus.textContent = `Deleting ${email}...`;
  const response = await fetch(`/api/admin/users/${encodeURIComponent(email)}?token=${encodeURIComponent(token)}`, { method: "DELETE" });
  const data = await response.json();
  if (!response.ok) {
    adminStatus.textContent = data.detail || "Delete failed";
    return;
  }
  adminStatus.textContent = `${data.deleted} deleted.`;
  loadUsers();
}

function renderResult(data) {
  const risk = data.analysis.risk_label;
  resultCard.innerHTML = `
    <div class="risk-band risk-${risk}">
      <div>
        <span>Risk triage</span>
        <h3>${risk}</h3>
      </div>
      <strong>${data.analysis.risk_score}/100</strong>
    </div>
    <h3>${data.patient_name}</h3>
    <p class="status">${data.id} | ${data.mode} mode | ${labelWorkflow(data.case_type)}</p>
    ${modelProfile(data.analysis.model_profile)}
    <div class="confidence-card">
      <strong>${data.analysis.confidence.level} confidence</strong>
      <span>${data.analysis.confidence.score}/100 | ${data.analysis.confidence.reasons.join(", ")}</span>
    </div>
    <div class="insight-section">
      <h4>AI explanation</h4>
      <p>${data.analysis.explanation}</p>
    </div>
    <div class="insight-section">
      <h4>Clinical impression</h4>
      <p>${data.analysis.clinical_impression}</p>
    </div>
    <div class="insight-section">
      <h4>Image interpretation</h4>
      <p>${data.analysis.image_interpretation}</p>
    </div>
    ${prescriptionExtraction(data.analysis.prescription_extraction)}
    ${informationGap(data.analysis)}
    ${medicineTable(data.analysis.medication_plan, data.case_type)}
    ${soapNote(data.analysis.soap_note)}
    ${listSection("Observations", data.analysis.observations)}
    ${listSection("Safety checks", data.analysis.safety_checks)}
    ${listSection("Recommended next steps", data.analysis.next_steps)}
    ${listSection("Follow-up questions", data.analysis.follow_up_questions)}
    ${listSection("Audit trail", data.audit || [])}
    <div class="approval-panel">
      <strong>${data.analysis.approval.status}</strong>
      <p>${data.analysis.approval.reason}</p>
      <div class="approval-actions">
        <button class="ghost-btn compact" type="button">Needs edit</button>
        <button class="primary-btn compact" type="button">Approve draft</button>
      </div>
    </div>
    ${data.transcript ? `<div class="insight-section"><h4>MedASR transcript</h4><p>${data.transcript}</p></div>` : ""}
    <div class="insight-section">
      <button class="primary-btn" onclick="downloadReport('${data.id}')">Download PDF report</button>
    </div>
  `;
}

function listSection(title, items) {
  if (!items || !items.length) return "";
  return `
    <div class="insight-section">
      <h4>${title}</h4>
      <ul>${items.map((item) => `<li>${item}</li>`).join("")}</ul>
    </div>
  `;
}

function downloadReport(caseId) {
  window.location.href = `/api/cases/${caseId}/report?token=${encodeURIComponent(token)}`;
}

function updateWorkflowFields() {
  const selected = document.querySelector("#caseType").value;
  document.querySelectorAll(".workflow-field").forEach((item) => {
    item.classList.toggle("hidden", item.dataset.workflow !== selected);
  });
}

function logout() {
  token = "";
  currentUser = null;
  localStorage.removeItem("vf_token");
  localStorage.removeItem("vf_user");
  workspace.classList.add("hidden");
  authPanel.classList.remove("hidden");
  adminPanel.classList.add("hidden");
  modeSelect.disabled = false;
  authForm.reset();
  authStatus.textContent = "Logged out. Please login or register.";
}

function labelWorkflow(value) {
  const labels = {
    general: "Multimodal reasoning",
    prescription: "Prescription / medicine",
    wound: "Wound follow-up",
    radiology: "Radiology-style",
    clinical_note: "Clinical documentation",
  };
  return labels[value] || value;
}

function medicineTable(items, caseType) {
  if (!items || !items.length) return "";
  if (caseType !== "prescription" && items[0].medicine === "Medicine names not confidently detected") return "";
  return `
    <div class="insight-section">
      <h4>Medicine and dosage guidance</h4>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Medicine</th><th>Dose</th><th>When to take</th><th>Duration</th><th>Notes</th></tr></thead>
          <tbody>
            ${items.map((item) => `
              <tr>
                <td>${item.medicine}</td>
                <td>${item.dose}</td>
                <td>${item.timing}</td>
                <td>${item.duration}</td>
                <td>${item.notes}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function prescriptionExtraction(extraction) {
  if (!extraction || !extraction.raw_text) return "";
  return `
    <div class="insight-section extraction-panel">
      <h4>Prescription text extracted from image</h4>
      <p>${extraction.raw_text}</p>
      <div class="mini-grid">
        <div><b>Status</b><span>${extraction.status}</span></div>
        <div><b>Vision confidence</b><span>${extraction.confidence}/100</span></div>
      </div>
      ${listSection("Clinical clues from prescription", extraction.clinical_clues || [])}
      ${listSection("Investigations found", extraction.investigations || [])}
      <p class="status">${extraction.warning || ""}</p>
    </div>
  `;
}

function informationGap(analysis) {
  if (!analysis.needs_more_information) return "";
  const questions = analysis.follow_up_questions || [];
  return `
    <div class="info-needed">
      <strong>More information needed before accurate guidance</strong>
      <p>The current case is missing: ${analysis.information_gap.join(", ")}.</p>
      <p>Ask the patient these follow-up questions, enter the answers in the follow-up answers box, and regenerate the insight.</p>
      ${questions.length ? `<ul>${questions.map((item) => `<li>${item}</li>`).join("")}</ul>` : ""}
    </div>
  `;
}

function modelProfile(profile) {
  if (!profile) return "";
  return `
    <div class="model-profile">
      <div>
        <strong>${profile.label}</strong>
        <span>${profile.deployment}</span>
      </div>
      <p>${profile.use}</p>
    </div>
  `;
}

function soapNote(note) {
  if (!note) return "";
  return `
    <div class="insight-section soap-grid">
      <h4>SOAP clinical note</h4>
      <div><b>S</b><p>${note.subjective}</p></div>
      <div><b>O</b><p>${note.objective}</p></div>
      <div><b>A</b><p>${note.assessment}</p></div>
      <div><b>P</b><p>${note.plan}</p></div>
    </div>
  `;
}

updateWorkflowFields();
