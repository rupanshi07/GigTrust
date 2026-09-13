const API = window.GIGTRUST_CONFIG.API_BASE_URL;

if (localStorage.getItem("gigtrust_logged_in") !== "true") {
  window.location.href = "index.html";
}

const userName = localStorage.getItem("gigtrust_name") || "GigTrust User";
const role = localStorage.getItem("gigtrust_role") || "user";

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
