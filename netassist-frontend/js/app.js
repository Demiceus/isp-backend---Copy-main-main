// Lightweight client-side session gate.
// The provided API has no login/auth endpoint,
// so this just remembers who's using the app locally.
// It does not authenticate against the backend.

function requireSession() {
  const raw = localStorage.getItem("netassist_user");

  if (!raw) {
    window.location.href = "index.html";
    return null;
  }

  return JSON.parse(raw);
}

function logout() {
  localStorage.removeItem("netassist_user");
  window.location.href = "index.html";
}

function initShell(activePage) {
  const user = requireSession();

  if (!user) return null;

  document.querySelectorAll(".nav-item[data-page]").forEach((el) => {
    el.classList.toggle("active", el.dataset.page === activePage);
  });

  const chip = document.getElementById("user-chip-name");

  if (chip) {
    chip.textContent = user.name;
  }

  const av = document.getElementById("user-avatar");

  if (av) {
    av.textContent = (user.name || "?").slice(0, 1).toUpperCase();
  }

  const btn = document.getElementById("logout-btn");

  if (btn) {
    btn.onclick = logout;
  }

  return user;
}

function toast(msg, kind = "info") {
  const el = document.createElement("div");

  el.className = "alert " + kind;

  el.style.cssText =
    "position:fixed;" +
    "bottom:20px;" +
    "right:20px;" +
    "z-index:80;" +
    "box-shadow:0 6px 20px rgba(0,0,0,.12);" +
    "max-width:340px";

  el.textContent = msg;

  document.body.appendChild(el);

  setTimeout(() => el.remove(), 3600);
}

function escHtml(s) {
  return (s ?? "")
    .toString()
    .replace(
      /[&<>]/g,
      (c) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
      })[c]
    );
}


// Render any object defensively as label/value rows.
function renderObjectAsKV(obj) {
  if (!obj || typeof obj !== "object") {
    return `
      <div class="kv">
        <span>Value</span>
        <span>${escHtml(obj)}</span>
      </div>
    `;
  }

  return Object.entries(obj)
    .map(
      ([k, v]) =>
        `<div class="kv">
          <span>${escHtml(k)}</span>
          <span>${escHtml(
            typeof v === "object" ? JSON.stringify(v) : v
          )}</span>
        </div>`
    )
    .join("");
}


/* =========================================================
   TYPING INDICATOR
   ========================================================= */

function showTypingIndicator() {
  const chat = document.querySelector(".chat-log");

  if (!chat) return;

  // Prevent duplicate indicators.
  if (document.getElementById("typing-indicator")) {
    return;
  }

  const typing = document.createElement("div");

  typing.className = "typing-bubble";
  typing.id = "typing-indicator";

  typing.innerHTML = `
    <span class="typing-dot"></span>
    <span class="typing-dot"></span>
    <span class="typing-dot"></span>
  `;

  chat.appendChild(typing);

  chat.scrollTop = chat.scrollHeight;
}

function hideTypingIndicator() {
  const typing = document.getElementById("typing-indicator");

  if (typing) {
    typing.remove();
  }
}


/* =========================================================
   CHAT MESSAGE DISPLAY
   ========================================================= */

function addChatMessage(text, sender) {
  const chat = document.querySelector(".chat-log");

  if (!chat) return;

  const message = document.createElement("div");

  message.className = `msg ${sender}`;

  message.innerHTML = escHtml(text).replace(/\n/g, "<br>");

  chat.appendChild(message);

  chat.scrollTop = chat.scrollHeight;
}


/* =========================================================
   SEND MESSAGE TO BACKEND
   ========================================================= */

async function sendChatMessage(sessionId, message) {
  if (!sessionId || !message) {
    return;
  }

  // Display customer's message immediately.
  addChatMessage(message, "customer");

  // Show ● ● ● while Ollama generates the response.
  showTypingIndicator();

  try {
    const result = await NetAssistAPI.sendMessage(
      sessionId,
      message
    );

    // Ollama finished.
    hideTypingIndicator();

    if (!result.ok) {
      addChatMessage(
        result.error ||
          "Sorry, something went wrong. Please try again.",
        "ai"
      );

      return;
    }

    const data = result.data;

    if (data && data.reply) {
      addChatMessage(data.reply, "ai");
    } else {
      addChatMessage(
        "I received your message, but I couldn't generate a response.",
        "ai"
      );
    }

  } catch (error) {
    hideTypingIndicator();

    console.error("Chat error:", error);

    addChatMessage(
      "Sorry, something went wrong. Please try again.",
      "ai"
    );
  }
}


/* =========================================================
   COMPLAINT TYPES
   ========================================================= */

const COMPLAINT_TYPES = [
  "slow_internet",
  "no_internet",
  "intermittent_connection",
  "router_modem",
  "service_outage",
  "billing",
  "installation",
  "plan_change",
  "technical_support",
  "account"
];

const COMPLAINT_TYPE_LABELS = {
  slow_internet: "Slow Internet",
  no_internet: "No Internet",
  intermittent_connection: "Intermittent Connection",
  router_modem: "Router/Modem",
  service_outage: "Service Outage",
  billing: "Billing",
  installation: "Installation",
  plan_change: "Plan Change",
  technical_support: "Technical Support",
  account: "Account"
};

/* =========================================================
   ADMIN SHELL (login gate + logout) used by admin pages
   ========================================================= */
function initAdmin() {
  const raw = localStorage.getItem("netassist_admin");
  if (!raw) { window.location.href = "admin-login.html"; return null; }
  const admin = JSON.parse(raw);
  if (!admin.token) { localStorage.removeItem("netassist_admin"); window.location.href = "admin-login.html"; return null; }
  const btn = document.getElementById("logout");
  if (btn) btn.onclick = () => { localStorage.removeItem("netassist_admin"); window.location.href = "index.html"; };
  const nm = document.getElementById("admin-name");
  if (nm) nm.textContent = admin.name || "Operations Admin";
  startNotifications();
  return admin;
}

/* Alerts agents when the AI (or a customer) escalates a case. */
function startNotifications() {
  let last = null;
  const poll = async () => {
    const r = await NetAssistAPI.getNotifications();
    if (!r.ok) return;
    const n = r.data.count;
    const link = document.querySelector('.admin-nav a[href="admin-escalations.html"]');
    if (link) link.textContent = "Escalation queue" + (n ? " (" + n + ")" : "");
    if (last !== null && n > last) toast("New escalation: a human agent is needed.", "warning");
    last = n;
  };
  poll();
  setInterval(poll, 15000);
}
