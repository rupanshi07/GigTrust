// Requires dashboard-common.js to already be loaded (authFetch, formatCurrency, escapeHtml).

const usersList = document.getElementById("usersList");
const gigsList = document.getElementById("gigsList");
const transactionsList = document.getElementById("transactionsList");

function statusBadgeClass(status) {
  const map = {
    OPEN: "badge-open",
    IN_PROGRESS: "badge-progress",
    COMPLETED: "badge-completed",
    CANCELLED: "badge-cancelled",
    ACTIVE: "badge-progress",
    CLIENT: "badge-open",
    FREELANCER: "badge-accepted",
    ADMIN: "badge-pending",
    SUCCESS: "badge-completed",
    FAILED: "badge-cancelled",
    ESCROW_FUND: "badge-progress",
    ESCROW_RELEASE: "badge-completed",
    ESCROW_REFUND: "badge-cancelled",
  };
  return map[status] || "badge-pending";
}

function badge(status) {
  return `<span class="badge ${statusBadgeClass(status)}">${escapeHtml(status)}</span>`;
}

// ---------------------------------------------------------
// ALL USERS
// ---------------------------------------------------------

async function loadUsers() {
  usersList.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const users = await authFetch("/admin/users");

    const clients = users.filter(u => u.role === "CLIENT").length;
    const freelancers = users.filter(u => u.role === "FREELANCER").length;

    document.getElementById("statTotalUsers").textContent = users.length;
    document.getElementById("statTotalUsersLabel").textContent = `${clients} clients, ${freelancers} freelancers`;

    if (users.length === 0) {
      usersList.innerHTML = "<p class='muted'>No users yet.</p>";
      return;
    }

    usersList.innerHTML = users.map(user => `
      <div class="item-row">
        <div class="item-row-head">
          <div>
            <strong>${escapeHtml(user.full_name)}</strong>
            <div class="item-meta">${escapeHtml(user.email)}</div>
          </div>
          <div>${badge(user.role)} <span class="item-meta">${formatCurrency(user.balance)}</span></div>
        </div>
      </div>`).join("");
  } catch (error) {
    usersList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

// ---------------------------------------------------------
// ALL GIGS
// ---------------------------------------------------------

async function loadGigs() {
  gigsList.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const gigs = await authFetch("/admin/gigs");

    const open = gigs.filter(g => g.status === "OPEN").length;
    const completed = gigs.filter(g => g.status === "COMPLETED").length;

    document.getElementById("statTotalGigs").textContent = gigs.length;
    document.getElementById("statTotalGigsLabel").textContent = `${open} open, ${completed} completed`;

    if (gigs.length === 0) {
      gigsList.innerHTML = "<p class='muted'>No gigs yet.</p>";
      return;
    }

    gigsList.innerHTML = gigs.map(gig => `
      <div class="item-row">
        <div class="item-row-head">
          <div>
            <strong>${escapeHtml(gig.title)}</strong>
            <div class="item-meta">Client: ${escapeHtml(gig.client_name)} &middot; Budget: ${formatCurrency(gig.budget)}</div>
          </div>
          ${badge(gig.status)}
        </div>
      </div>`).join("");
  } catch (error) {
    gigsList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

// ---------------------------------------------------------
// ALL TRANSACTIONS
// ---------------------------------------------------------

async function loadTransactions() {
  transactionsList.innerHTML = "<p class='muted'>Loading...</p>";
  try {
    const transactions = await authFetch("/admin/transactions");

    const totalVolume = transactions.reduce((sum, t) => sum + Number(t.amount), 0);

    document.getElementById("statTotalTransactions").textContent = transactions.length;
    document.getElementById("statTotalTransactionsLabel").textContent = `Total volume: ${formatCurrency(totalVolume)}`;

    if (transactions.length === 0) {
      transactionsList.innerHTML = "<p class='muted'>No transactions yet.</p>";
      return;
    }

    transactionsList.innerHTML = transactions.map(tx => `
      <div class="item-row">
        <div class="item-row-head">
          <div>
            <strong>${formatCurrency(tx.amount)}</strong>
            <div class="item-meta">
              From: ${escapeHtml(tx.sender_name)}
              ${tx.receiver_name ? ` &rarr; To: ${escapeHtml(tx.receiver_name)}` : ""}
            </div>
          </div>
          <div>${badge(tx.transaction_type)} ${badge(tx.status)}</div>
        </div>
      </div>`).join("");
  } catch (error) {
    transactionsList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

// ---------------------------------------------------------
// INITIAL LOAD
// ---------------------------------------------------------

loadUsers();
loadGigs();
loadTransactions();