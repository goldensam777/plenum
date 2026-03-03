/* app.js — Logique frontend du Plenum
   =====================================
   Consomme l'API FastAPI (server.py) et construit l'UI dynamiquement.
   Aucun framework — DOM vanilla pur.
*/

// ── État local ───────────────────────────────────────────────────────────────
let turnCount = 0;
let agentStatus = {};   // { Claude: {available, model}, ... }

// ── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  await loadStatus();
  setupForm();
  setupMenu();
  setupModal();
  autoResizeTextarea();
});

// ── Chargement de l'état des agents ──────────────────────────────────────────
async function loadStatus() {
  try {
    const res = await fetch("/status");
    agentStatus = await res.json();
    renderAgentPills();
  } catch (e) {
    console.error("Impossible de charger le statut des agents", e);
  }
}

function renderAgentPills() {
  const container = document.getElementById("agent-pills");
  container.className = "agent-pills";
  container.innerHTML = "";
  for (const [name, info] of Object.entries(agentStatus)) {
    const pill = document.createElement("span");
    pill.className = `pill ${info.available ? "ok" : "off"}`;
    pill.textContent = info.available ? `✓ ${name}` : `✗ ${name}`;
    container.appendChild(pill);
  }
}

// ── Formulaire de chat ────────────────────────────────────────────────────────
function setupForm() {
  const form  = document.getElementById("chat-form");
  const input = document.getElementById("input");
  const btn   = document.getElementById("btn-send");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    input.value = "";
    resizeTextarea(input);
    btn.disabled = true;

    // Cache l'écran d'accueil au premier envoi
    document.getElementById("welcome").style.display = "none";

    await sendMessage(message);
    btn.disabled = false;
    input.focus();
  });

  // Entrée = envoyer, Shift+Entrée = nouvelle ligne
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event("submit"));
    }
  });
}

async function sendMessage(message) {
  turnCount++;
  document.getElementById("turn-counter").textContent = `Tour ${turnCount}`;

  // Crée le bloc du tour avec le message + cartes en attente
  const turnEl = createTurnBlock(turnCount, message);
  document.getElementById("history").appendChild(turnEl);
  scrollToBottom();

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(`Erreur : ${err.detail}`, "error");
      removeLoadingCards(turnEl);
      return;
    }

    const data = await res.json();
    turnCount = data.turn;
    document.getElementById("turn-counter").textContent = `Tour ${turnCount}`;

    fillResponseCards(turnEl, data.responses);

  } catch (e) {
    showToast("Erreur réseau", "error");
    removeLoadingCards(turnEl);
  }

  scrollToBottom();
}

// ── Construction du DOM d'un tour ─────────────────────────────────────────────
function createTurnBlock(turn, userMessage) {
  const turnEl = document.createElement("div");
  turnEl.className = "turn";
  turnEl.dataset.turn = turn;

  // En-tête du tour
  const header = document.createElement("div");
  header.className = "turn-header";
  header.textContent = `Tour ${turn}`;
  turnEl.appendChild(header);

  // Message de Samuel
  const userEl = document.createElement("div");
  userEl.className = "user-message";
  userEl.innerHTML = `<div class="author">Samuel</div><div>${escapeHtml(userMessage)}</div>`;
  turnEl.appendChild(userEl);

  // Grille des cartes agents (en attente)
  const grid = document.createElement("div");
  grid.className = "agents-grid";
  turnEl.appendChild(grid);

  for (const [name, info] of Object.entries(agentStatus)) {
    if (!info.available) continue;
    grid.appendChild(createLoadingCard(name));
  }

  return turnEl;
}

function createLoadingCard(name) {
  const card = document.createElement("div");
  card.className = "agent-card";
  card.dataset.agent = name;

  card.innerHTML = `
    <div class="agent-card-header">
      <span class="agent-name">${name}</span>
      <span class="agent-meta"><span class="spinner"></span></span>
    </div>
    <div class="loading-body"><span class="spinner"></span></div>
  `;
  return card;
}

function fillResponseCards(turnEl, responses) {
  const grid = turnEl.querySelector(".agents-grid");

  for (const [name, resp] of Object.entries(responses)) {
    // Cherche la carte existante ou crée-la si l'agent n'était pas dans agentStatus
    let card = grid.querySelector(`[data-agent="${name}"]`);
    if (!card) {
      card = document.createElement("div");
      card.className = "agent-card";
      card.dataset.agent = name;
      grid.appendChild(card);
    }

    if (resp.success) {
      card.innerHTML = `
        <div class="agent-card-header">
          <span class="agent-name">${name}</span>
          <span class="agent-meta">
            <span class="agent-status ok">✓</span>
            <span>${resp.latency_ms} ms</span>
          </span>
        </div>
        <div class="agent-card-body">${marked.parse(resp.content)}</div>
      `;
    } else {
      card.innerHTML = `
        <div class="agent-card-header">
          <span class="agent-name">${name}</span>
          <span class="agent-meta"><span class="agent-status err">✗</span></span>
        </div>
        <div class="error-body">${escapeHtml(resp.error || "Erreur inconnue")}</div>
      `;
    }
  }
}

function removeLoadingCards(turnEl) {
  turnEl.querySelectorAll(".loading-body").forEach(el => {
    el.closest(".agent-card").innerHTML = `
      <div class="error-body">Réponse non reçue.</div>`;
  });
}

// ── Menu contextuel ───────────────────────────────────────────────────────────
function setupMenu() {
  const btn  = document.getElementById("btn-menu");
  const menu = document.getElementById("menu");

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    menu.classList.toggle("hidden");
  });

  document.addEventListener("click", () => menu.classList.add("hidden"));

  document.getElementById("btn-reset").addEventListener("click", async () => {
    menu.classList.add("hidden");
    await fetch("/reset", { method: "POST" });
    document.getElementById("history").innerHTML = "";
    document.getElementById("welcome").style.display = "";
    turnCount = 0;
    document.getElementById("turn-counter").textContent = "Tour 0";
    showToast("Session réinitialisée.");
  });

  document.getElementById("btn-export").addEventListener("click", async () => {
    menu.classList.add("hidden");
    const res = await fetch("/export", { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      showToast(`Session exportée → ${data.path}`);
    } else {
      const err = await res.json();
      showToast(err.detail, "error");
    }
  });

  document.getElementById("btn-sessions").addEventListener("click", async () => {
    menu.classList.add("hidden");
    const res = await fetch("/sessions");
    const data = await res.json();
    showSessionsModal(data.sessions);
  });

  document.getElementById("btn-status").addEventListener("click", async () => {
    menu.classList.add("hidden");
    await loadStatus();
    showStatusModal();
  });
}

// ── Modal ────────────────────────────────────────────────────────────────────
function setupModal() {
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-overlay").addEventListener("click", (e) => {
    if (e.target === document.getElementById("modal-overlay")) closeModal();
  });
}

function showSessionsModal(sessions) {
  document.getElementById("modal-title").textContent = "Sessions sauvegardées";
  const body = document.getElementById("modal-body");
  if (!sessions.length) {
    body.innerHTML = `<p style="color:var(--muted)">Aucune session sauvegardée.</p>`;
  } else {
    body.innerHTML = sessions.map(s => `
      <div class="session-item">
        <strong>${s.name}</strong>
        ${s.message_count} messages · ${s.saved_at.slice(0, 16).replace("T", " ")}
      </div>
    `).join("");
  }
  document.getElementById("modal-overlay").classList.remove("hidden");
}

function showStatusModal() {
  document.getElementById("modal-title").textContent = "État des agents";
  const body = document.getElementById("modal-body");
  body.innerHTML = Object.entries(agentStatus).map(([name, info]) => `
    <div class="session-item">
      <strong>${info.available ? "✓" : "✗"} ${name}</strong>
      ${info.model}
    </div>
  `).join("");
  document.getElementById("modal-overlay").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
}

// ── Utilitaires ───────────────────────────────────────────────────────────────
function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.textContent = message;
  Object.assign(toast.style, {
    position: "fixed",
    bottom: "90px",
    left: "50%",
    transform: "translateX(-50%)",
    background: type === "error" ? "var(--red)" : "var(--green)",
    color: "#fff",
    padding: "10px 18px",
    borderRadius: "8px",
    fontSize: "0.85rem",
    zIndex: "999",
    maxWidth: "90vw",
    textAlign: "center",
    boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
  });
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function autoResizeTextarea() {
  const input = document.getElementById("input");
  input.addEventListener("input", () => resizeTextarea(input));
}

function resizeTextarea(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}
