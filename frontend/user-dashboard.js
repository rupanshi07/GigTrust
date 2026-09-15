// Requires dashboard-common.js to already be loaded (authFetch, formatCurrency, escapeHtml).

const postGigForm = document.getElementById("postGigForm");
const postGigMessage = document.getElementById("postGigMessage");
const myGigsList = document.getElementById("myGigsList");
const myContractsList = document.getElementById("myContractsList");

function statusBadgeClass(status) {
  const map = {
    OPEN: "badge-open",
    IN_PROGRESS: "badge-progress",
    COMPLETED: "badge-completed",
    CANCELLED: "badge-cancelled",
    ACTIVE: "badge-progress",
    WORK_SUBMITTED: "badge-progress",
    UNFUNDED: "badge-pending",
    HELD: "badge-progress",
    RELEASED: "badge-completed",
    PENDING: "badge-pending",
    ACCEPTED: "badge-accepted",
    REJECTED: "badge-rejected",
  };
  return map[status] || "badge-pending";
}

function badge(status) {
  return `<span class="badge ${statusBadgeClass(status)}">${escapeHtml(status)}</span>`;
}

// ---------------------------------------------------------
// POST A NEW GIG
// ---------------------------------------------------------

postGigForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  postGigMessage.textContent = "";
  postGigMessage.className = "";

  const title = document.getElementById("gigTitle").value.trim();
  const description = document.getElementById("gigDescription").value.trim();
  const budget = parseFloat(document.getElementById("gigBudget").value);

  try {
    await authFetch("/gigs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description, budget }),
    });

    postGigMessage.textContent = "Gig posted successfully.";
    postGigMessage.className = "inline-success";
    postGigForm.reset();
    loadMyGigs();
  } catch (error) {
    postGigMessage.textContent = error.message;
    postGigMessage.className = "inline-error";
  }
});

// ---------------------------------------------------------
// MY GIGS + BIDS
// ---------------------------------------------------------

async function loadMyGigs() {
  myGigsList.innerHTML = "<p class='muted'>Loading...</p>";

  try {
    const gigs = await authFetch("/gigs/mine");

    if (gigs.length === 0) {
      myGigsList.innerHTML = "<p class='muted'>You haven't posted any gigs yet.</p>";
      return;
    }

    myGigsList.innerHTML = gigs
      .map(
        (gig) => `
        <div class="item-row" data-gig-id="${gig.gig_id}">
          <div class="item-row-head">
            <div>
              <strong>${escapeHtml(gig.title)}</strong>
              <div class="item-meta">Budget: ${formatCurrency(gig.budget)}</div>
            </div>
            ${badge(gig.status)}
          </div>
          ${
            gig.status === "OPEN"
              ? `<button class="btn-small secondary view-bids-btn" data-gig-id="${gig.gig_id}">View Bids</button>`
              : ""
          }
          <div class="bids-box hidden" id="bids-for-${gig.gig_id}"></div>
        </div>`
      )
      .join("");

    document.querySelectorAll(".view-bids-btn").forEach((btn) => {
      btn.addEventListener("click", () => toggleBids(btn.dataset.gigId));
    });
  } catch (error) {
    myGigsList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

async function toggleBids(gigId) {
  const box = document.getElementById(`bids-for-${gigId}`);

  if (!box.classList.contains("hidden")) {
    box.classList.add("hidden");
    return;
  }

  box.classList.remove("hidden");
  box.innerHTML = "<p class='muted'>Loading bids...</p>";

  try {
    const bids = await authFetch(`/gigs/${gigId}/bids`);

    if (bids.length === 0) {
      box.innerHTML = "<p class='muted'>No bids yet.</p>";
      return;
    }

    box.innerHTML = bids
      .map(
        (bid) => `
        <div class="item-row">
          <div class="item-row-head">
            <div>
              <strong>${formatCurrency(bid.bid_amount)}</strong>
              <div class="item-meta">${escapeHtml(bid.proposal || "")}</div>
            </div>
            ${badge(bid.status)}
          </div>
          ${
            bid.status === "PENDING"
              ? `<button class="btn-small accept-bid-btn" data-bid-id="${bid.bid_id}">Accept Bid</button>`
              : ""
          }
          <div class="inline-error accept-error" id="accept-error-${bid.bid_id}"></div>
        </div>`
      )
      .join("");

    document.querySelectorAll(".accept-bid-btn").forEach((btn) => {
      btn.addEventListener("click", () => acceptBid(btn.dataset.bidId, gigId));
    });
  } catch (error) {
    box.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

async function acceptBid(bidId, gigId) {
  const errorBox = document.getElementById(`accept-error-${bidId}`);
  errorBox.textContent = "";

  try {
    const result = await authFetch(`/bids/${bidId}/accept`, { method: "POST" });

    let message = `Bid accepted. Contract #${result.contract_id} created.`;
    if (result.fraud_score) {
      message += ` Risk: ${result.fraud_score.risk_tier} (${result.fraud_score.risk_score} pts).`;
    }

    alert(message);
    loadMyGigs();
    loadMyContracts();
  } catch (error) {
    errorBox.textContent = error.message;
  }
}

// ---------------------------------------------------------
// MY CONTRACTS (fund escrow / approve / view fraud score)
// ---------------------------------------------------------

async function loadMyContracts() {
  myContractsList.innerHTML = "<p class='muted'>Loading...</p>";

  try {
    const contracts = await authFetch("/contracts/mine");

    if (contracts.length === 0) {
      myContractsList.innerHTML = "<p class='muted'>No contracts yet.</p>";
      return;
    }

    myContractsList.innerHTML = contracts
      .map((contract) => {
        let actionButton = "";

        if (contract.contract_status === "ACTIVE" && contract.escrow_status === "UNFUNDED") {
          actionButton = `<button class="btn-small fund-btn" data-contract-id="${contract.contract_id}">Fund Escrow</button>`;
        } else if (contract.contract_status === "WORK_SUBMITTED") {
          actionButton = `<button class="btn-small approve-btn" data-contract-id="${contract.contract_id}">Approve &amp; Release</button>`;
        }

        return `
        <div class="item-row">
          <div class="item-row-head">
            <div>
              <strong>${escapeHtml(contract.gig_title)}</strong>
              <div class="item-meta">
                Freelancer: ${escapeHtml(contract.freelancer_name)} &middot;
                ${formatCurrency(contract.agreed_amount)}
              </div>
            </div>
            <div>${badge(contract.contract_status)} ${badge(contract.escrow_status)}</div>
          </div>
          ${actionButton}
          <button class="btn-small secondary fraud-btn" data-contract-id="${contract.contract_id}">View Fraud Score</button>
          <div class="inline-error contract-error" id="contract-error-${contract.contract_id}"></div>
          <div class="fraud-box hidden" id="fraud-box-${contract.contract_id}"></div>
        </div>`;
      })
      .join("");

    document.querySelectorAll(".fund-btn").forEach((btn) => {
      btn.addEventListener("click", () => fundEscrow(btn.dataset.contractId));
    });
    document.querySelectorAll(".approve-btn").forEach((btn) => {
      btn.addEventListener("click", () => approveContract(btn.dataset.contractId));
    });
    document.querySelectorAll(".fraud-btn").forEach((btn) => {
      btn.addEventListener("click", () => toggleFraudScore(btn.dataset.contractId));
    });
  } catch (error) {
    myContractsList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

async function fundEscrow(contractId) {
  const errorBox = document.getElementById(`contract-error-${contractId}`);
  errorBox.textContent = "";

  try {
    await authFetch(`/contracts/${contractId}/fund-escrow`, { method: "POST" });
    loadMyContracts();
  } catch (error) {
    errorBox.textContent = error.message;
  }
}

async function approveContract(contractId) {
  const errorBox = document.getElementById(`contract-error-${contractId}`);
  errorBox.textContent = "";

  try {
    const result = await authFetch(`/contracts/${contractId}/approve`, { method: "POST" });
    alert(`Payment of ${formatCurrency(result.released_amount)} released to the freelancer.`);
    loadMyContracts();
  } catch (error) {
    errorBox.textContent = error.message;
  }
}

async function toggleFraudScore(contractId) {
  const box = document.getElementById(`fraud-box-${contractId}`);

  if (!box.classList.contains("hidden")) {
    box.classList.add("hidden");
    return;
  }

  box.classList.remove("hidden");
  box.innerHTML = "Loading...";

  try {
    const score = await authFetch(`/fraud/score/contract/${contractId}`);
    box.innerHTML = `
      <strong>Risk: ${escapeHtml(score.risk_tier)} (${score.risk_score} pts)</strong>
      <ul>${score.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>
    `;
  } catch (error) {
    box.innerHTML = `<span class="inline-error">${escapeHtml(error.message)}</span>`;
  }
}

// ---------------------------------------------------------
// INITIAL LOAD
// ---------------------------------------------------------

loadMyGigs();
loadMyContracts();
