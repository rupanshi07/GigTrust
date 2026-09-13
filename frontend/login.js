const API = window.GIGTRUST_CONFIG.API_BASE_URL;

async function checkBackend() {
  const status = document.getElementById("backendStatus");
  const dot = document.getElementById("backendDot");

  try {
    const res = await fetch(`${API}/health/database`);
    if (!res.ok) throw new Error("Backend returned an error");

    const data = await res.json();
    const text = JSON.stringify(data).toLowerCase();

    if (text.includes("connected")) {
      status.textContent = "Azure backend connected";
      dot.className = "dot ok";
      return true;
    }

    status.textContent = "Backend reachable, database unavailable";
    dot.className = "dot fail";
    return true;
  } catch (err) {
    status.textContent = "Backend not reachable";
    dot.className = "dot fail";
    return false;
  }
}

checkBackend();

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();

  const message = document.getElementById("loginMessage");
  const button = document.getElementById("loginButton");
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  button.disabled = true;
  button.textContent = "Connecting...";
  message.textContent = "";

  const backendReachable = await checkBackend();

  if (!backendReachable) {
    message.textContent = "Cannot reach the GigTrust backend. Check CORS or backend status.";
    button.disabled = false;
    button.textContent = "Login";
    return;
  }

  if (email === "demo@gigtrust.com" && password === "gigtrust123") {
    localStorage.setItem("gigtrust_logged_in", "true");
    window.location.href = "dashboard.html";
  } else {
    message.textContent = "Invalid demo credentials.";
    button.disabled = false;
    button.textContent = "Login";
  }
});
