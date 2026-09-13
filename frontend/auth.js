const API = window.GIGTRUST_CONFIG.API_BASE_URL;

let selectedRole = "user";
let selectedMode = "login";

const roleTabs = document.querySelectorAll(".role-tab");
const modeTabs = document.querySelectorAll(".mode-tab");
const modeTabsContainer = document.getElementById("modeTabs");
const nameGroup = document.getElementById("nameGroup");
const adminNote = document.getElementById("adminNote");
const submitButton = document.getElementById("submitButton");
const title = document.getElementById("formTitle");
const subtitle = document.getElementById("formSubtitle");
const message = document.getElementById("authMessage");

async function checkBackend() {
  const status = document.getElementById("backendStatus");
  const dot = document.getElementById("backendDot");

  try {
    const response = await fetch(`${API}/health`);
    const data = await response.json();

    if (response.ok && data.status === "healthy") {
      status.textContent = "Backend connected";
      dot.className = "dot ok";
      return;
    }

    throw new Error("Unhealthy backend");
  } catch {
    status.textContent = "Backend not reachable";
    dot.className = "dot fail";
  }
}

function updateForm() {
  message.textContent = "";

  const isAdmin = selectedRole === "admin";

  if (isAdmin) {
    selectedMode = "login";
    modeTabsContainer.classList.add("hidden");
    nameGroup.classList.add("hidden");
    adminNote.classList.remove("hidden");
    title.textContent = "Admin Login";
    subtitle.textContent = "Administrator access uses fixed backend credentials.";
    submitButton.textContent = "Login as Admin";
  } else {
    modeTabsContainer.classList.remove("hidden");
    adminNote.classList.add("hidden");

    if (selectedMode === "register") {
      nameGroup.classList.remove("hidden");
      title.textContent =
        selectedRole === "user" ? "Create User Account" : "Create Freelancer Account";
      subtitle.textContent = "Your account will be stored securely in MongoDB.";
      submitButton.textContent = "Create Account";
    } else {
      nameGroup.classList.add("hidden");
      title.textContent =
        selectedRole === "user" ? "User Login" : "Freelancer Login";
      subtitle.textContent =
        selectedRole === "user"
          ? "Sign in to your client account."
          : "Sign in to your freelancer account.";
      submitButton.textContent =
        selectedRole === "user" ? "Login as User" : "Login as Freelancer";
    }
  }
}

roleTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    roleTabs.forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    selectedRole = tab.dataset.role;
    updateForm();
  });
});

modeTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    modeTabs.forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    selectedMode = tab.dataset.mode;
    updateForm();
  });
});

document.getElementById("authForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  message.textContent = "";

  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  submitButton.disabled = true;

  try {
    if (selectedMode === "register" && selectedRole !== "admin") {
      submitButton.textContent = "Creating account...";

      const response = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email,
          password,
          role: selectedRole,
        }),
      });

      const data = await response.json();

      if (data.status !== "success") {
        throw new Error(data.message || "Registration failed.");
      }

      message.className = "form-message success";
      message.textContent = "Account created. You can now log in.";

      selectedMode = "login";
      modeTabs.forEach((item) => {
        item.classList.toggle("active", item.dataset.mode === "login");
      });
      updateForm();
      return;
    }

    submitButton.textContent = "Signing in...";

    const response = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        password,
        role: selectedRole,
      }),
    });

    const data = await response.json();

    if (data.status !== "success") {
      throw new Error(data.message || "Login failed.");
    }

    localStorage.setItem("gigtrust_logged_in", "true");
    localStorage.setItem("gigtrust_role", data.user.role);
    localStorage.setItem("gigtrust_name", data.user.name);
    localStorage.setItem("gigtrust_email", data.user.email);

    if (data.user.role === "admin") {
      window.location.href = "admin-dashboard.html";
    } else if (data.user.role === "freelancer") {
      window.location.href = "freelancer-dashboard.html";
    } else {
      window.location.href = "user-dashboard.html";
    }
  } catch (error) {
    message.className = "form-message";
    message.textContent = error.message;
  } finally {
    submitButton.disabled = false;
    updateForm();
  }
});

checkBackend();
updateForm();
