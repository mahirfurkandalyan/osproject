const elements = {
  schedulerMode: document.getElementById("schedulerMode"),
  tickValue: document.getElementById("tickValue"),
  runningPid: document.getElementById("runningPid"),
  schedulerBadge: document.getElementById("schedulerBadge"),
  ramText: document.getElementById("ramText"),
  ramPercent: document.getElementById("ramPercent"),
  memoryFill: document.getElementById("memoryFill"),
  processCount: document.getElementById("processCount"),
  stateStrip: document.getElementById("stateStrip"),
  processTable: document.getElementById("processTable"),
  logPanel: document.getElementById("logPanel"),
  lockPanel: document.getElementById("lockPanel"),
  filePanel: document.getElementById("filePanel"),
};

async function api(path, method = "GET", body = null) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : null,
  });
  return response.json();
}

function renderProcessRows(processes) {
  elements.processCount.textContent = `${processes.length} apps`;
  const states = ["NEW", "READY", "RUNNING", "BLOCKED", "TERMINATED"];
  const counts = Object.fromEntries(states.map((state) => [state, 0]));
  processes.forEach((process) => {
    counts[process.state] = (counts[process.state] || 0) + 1;
  });
  elements.stateStrip.innerHTML = states.map((state) => `
    <span class="state ${state} state-counter">${state}: ${counts[state]}</span>
  `).join("");
  elements.processTable.innerHTML = processes.map((process) => {
    const waitText = process.waiting_resource || process.block_reason || "None";
    const boosted = process.effective_priority > process.priority;
    const rowClass = [
      process.state === "RUNNING" ? "running-row" : "",
      process.state === "BLOCKED" ? "blocked-row" : "",
      boosted ? "boosted-row" : "",
    ].filter(Boolean).join(" ");
    return `
      <tr class="${rowClass}">
        <td>P${process.pid}</td>
        <td>${process.name}</td>
        <td><span class="state ${process.state}">${process.state}</span></td>
        <td>${process.memory_mb} MB</td>
        <td>
          <span class="${boosted ? "priority-boost" : ""}">${process.effective_priority}</span>
          <span class="subtle">(base ${process.priority})</span>
          ${boosted ? '<span class="boost-badge">INHERITED</span>' : ""}
        </td>
        <td><span class="${process.state === "BLOCKED" ? "reason-badge" : ""}">${waitText}</span></td>
      </tr>
    `;
  }).join("");
}

function renderLocks(locks) {
  elements.lockPanel.innerHTML = locks.map((lock) => `
    <div class="mini-item">
      <strong>${lock.name}</strong>
      <div>Owner: ${lock.owner_pid ? `P${lock.owner_pid}` : "Free"}</div>
      <div>Waiting: ${lock.wait_queue.length ? lock.wait_queue.map((pid) => `P${pid}`).join(", ") : "None"}</div>
    </div>
  `).join("");
}

function renderFiles(files) {
  if (!files.length) {
    elements.filePanel.innerHTML = '<div class="mini-item">No files created yet.</div>';
    return;
  }
  elements.filePanel.innerHTML = files.map((file) => `
    <div class="mini-item">
      <strong>${file.name}</strong>
      <div>${file.content || "(empty file)"}</div>
    </div>
  `).join("");
}

function renderLogs(logs) {
  elements.logPanel.innerHTML = logs.map((entry) => `<div class="log-entry">${entry}</div>`).join("");
  elements.logPanel.scrollTop = elements.logPanel.scrollHeight;
}

function render(state) {
  elements.schedulerMode.textContent = state.scheduler === "ROUND_ROBIN" ? "Round Robin" : "FIFO";
  elements.schedulerBadge.textContent = state.scheduler === "ROUND_ROBIN" ? `RR q=${state.quantum}` : "FIFO";
  elements.tickValue.textContent = state.tick;
  elements.runningPid.textContent = state.current_pid ? `P${state.current_pid}` : "Idle";
  elements.ramText.textContent = `${state.ram_used_mb} / ${state.ram_total_mb} MB`;
  elements.ramPercent.textContent = `${state.ram_percent}% used`;
  elements.memoryFill.style.width = `${Math.min(state.ram_percent, 100)}%`;
  renderProcessRows(state.processes);
  renderLocks(state.locks);
  renderFiles(state.files);
  renderLogs(state.logs);
}

async function refresh() {
  const state = await api("/api/state");
  render(state);
}

async function handleAction(action) {
  const routes = {
    "open-app": ["/api/apps/open", "POST"],
    "close-app": ["/api/apps/close", "POST"],
    "switch-scheduler": ["/api/scheduler/switch", "POST"],
    "file-io": ["/api/events/file-io", "POST"],
    "memory-pressure": ["/api/events/memory-pressure", "POST"],
    "lock-conflict": ["/api/events/lock-conflict", "POST"],
    "priority-inversion": ["/api/events/priority-inversion", "POST"],
    "failure": ["/api/events/failure", "POST"],
    "reset": ["/api/reset", "POST"],
  };

  const [path, method] = routes[action];
  const state = await api(path, method);
  render(state);
}

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => handleAction(button.dataset.action));
});

refresh();
setInterval(refresh, 1200);
