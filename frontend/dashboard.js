const API = window.GIGTRUST_CONFIG.API_BASE_URL;

if (localStorage.getItem("gigtrust_logged_in") !== "true") {
  window.location.href = "index.html";
}

document.getElementById("apiUrl").textContent = `Backend: ${API}`;

document.getElementById("logoutBtn").addEventListener("click", () => {
  localStorage.removeItem("gigtrust_logged_in");
  window.location.href = "index.html";
});

async function check(path, statusId, dotId) {
  const status = document.getElementById(statusId);
  const dot = document.getElementById(dotId);

  status.textContent = "Checking...";
  dot.className = "status-dot";

  try {
    const res = await fetch(`${API}${path}`);
    const data = await res.json();
    const text = JSON.stringify(data).toLowerCase();

    const healthy = res.ok && !text.includes('"status":"failed"') && !text.includes('"status": "failed"');

    status.textContent = healthy ? "Connected" : "Failed";
    dot.className = healthy ? "status-dot ok" : "status-dot fail";
  } catch (err) {
    status.textContent = "Connection error";
    dot.className = "status-dot fail";
  }
}

async function loadHealth() {
  await Promise.all([
    check("/health/database", "sqlStatus", "sqlDot"),
    check("/health/mongodb", "mongoStatus", "mongoDot"),
    check("/health/cassandra", "cassandraStatus", "cassandraDot")
  ]);
}

document.getElementById("refreshHealth").addEventListener("click", loadHealth);
loadHealth();
