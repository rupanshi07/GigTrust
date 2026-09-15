const API = window.GIGTRUST_CONFIG.API_BASE_URL;

if (localStorage.getItem("gigtrust_logged_in") !== "true") {
  window.location.href = "index.html";
}

const userName = localStorage.getItem("gigtrust_name") || "GigTrust User";
const role = localStorage.getItem("gigtrust_role") || "user";
const token = localStorage.getItem("gigtrust_token");
const sqlUserId = localStorage.getItem("gigtrust_sql_user_id");

const welcomeName = document.getElementById("welcomeName");
if (welcomeName) {
  welcomeName.textContent = userName;
}

const apiUrl = document.getElementById("apiUrl");
if (apiUrl) {
  apiUrl.textContent = `Backend: ${API}`;
}

document.getElementById("logoutBtn").addEventListener("click", () => {
  localStorage.clear();
  window.location.href = "index.html";
});

async function authFetch(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
    Authorization: `Bearer ${token}`,
  };
  const response = await fetch(`${API}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message =
      (data.detail && (data.detail.message || data.detail)) ||
      "Request failed.";
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  return data;
}

function formatCurrency(amount) {
  return "₹" + Number(amount).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

async function check(path, statusId, dotId) {
  const status = document.getElementById(statusId);
  const dot = document.getElementById(dotId);

  status.textContent = "Checking...";
  dot.className = "status-dot";

  try {
    const response = await fetch(`${API}${path}`);
    const data = await response.json();
    const text = JSON.stringify(data).toLowerCase();

    const healthy =
      response.ok &&
      !text.includes('"status":"failed"') &&
      !text.includes('"status": "failed"');

    status.textContent = healthy ? "Connected" : "Failed";
    dot.className = healthy ? "status-dot ok" : "status-dot fail";
  } catch {
    status.textContent = "Connection error";
    dot.className = "status-dot fail";
  }
}

async function loadHealth() {
  await Promise.all([
    check("/health/database", "sqlStatus", "sqlDot"),
    check("/health/mongodb", "mongoStatus", "mongoDot"),
    check("/health/cassandra", "cassandraStatus", "cassandraDot"),
  ]);
}

document.getElementById("refreshHealth").addEventListener("click", loadHealth);
loadHealth();