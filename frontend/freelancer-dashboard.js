// Requires dashboard-common.js to already be loaded (authFetch, formatCurrency, escapeHtml).

const browseGigsList = document.getElementById("browseGigsList");
const myBidsList = document.getElementById("myBidsList");
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
// BROWSE OPEN GIGS + PLACE A BID
// ---------------------------------------------------------

async function loadOpenGigs() {
  browseGigsList.innerHTML = "<p class='muted'>Loading...</p>";

  try {
    const gigs = await authFetch("/gigs");

    if (gigs.length === 0) {
      browseGigsList.innerHTML = "<p class='muted'>No open gigs right now.</p>";
      return;
    }

    browseGigsList.innerHTML = gigs
      .map(
        (gig) => `
        <div class="item-row">
          <div class="item-row-head">
            <div>
              <strong>${escapeHtml(gig.title)}</strong>
              <div class="item-meta">${escapeHtml(gig.description || "")}</div>
              <div class="item-meta">Budget: ${formatCurrency(gig.budget)}</div>
            </div>
            ${badge(gig.status)}
          </div>
          <button class="btn-small secondary bid-toggle-btn" data-gig-id="${gig.gig_id}">Place a Bid</button>
          <div class="bids-box hidden" id="bid-form-${gig.gig_id}">
            <form class="inline-form bid-form" data-gig-id="${gig.gig_id}">
              <input type="number" step="0.01" min="1" placeholder="Your bid amount (₹)" class="bid-amount-input" required />
              <textarea placeholder="Your proposal" class="bid-proposal-input" required></textarea>
              <button type="submit" class="btn-small">Submit Bid</button>
            </form>
            <div class="inline-error bid-error" id="bid-error-${gig.gig_id}"></div>
            <div class="inline-success bid-success" id="bid-success-${gig.gig_id}"></div>
          </div>
        </div>`
      )
      .join("");

    document.querySelectorAll(".bid-toggle-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById(`bid-form-${btn.dataset.gigId}`).classList.toggle("hidden");
      });
    });

    document.querySelectorAll(".bid-form").forEach((form) => {
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const gigId = form.dataset.gigId;
        const errorBox = document.getElementById(`bid-error-${gigId}`);
        const successBox = document.getElementById(`bid-success-${gigId}`);
        errorBox.textContent = "";
        successBox.textContent = "";

        const bidAmount = parseFloat(form.querySelector(".bid-amount-input").value);
        const proposal = form.querySelector(".bid-proposal-input").value.trim();

        try {
          await authFetch(`/gigs/${gigId}/bids`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bid_amount: bidAmount, proposal }),
          });

          successBox.textContent = "Bid submitted successfully.";
          form.reset();
          loadMyBids();
        } catch (error) {
          errorBox.textContent = error.message;
        }
      });
    });
  } catch (error) {
    browseGigsList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

// ---------------------------------------------------------
// MY BIDS
// ---------------------------------------------------------

async function loadMyBids() {
  myBidsList.innerHTML = "<p class='muted'>Loading...</p>";

  try {
    const bids = await authFetch("/bids/mine");

    if (bids.length === 0) {
      myBidsList.innerHTML = "<p class='muted'>You haven't placed any bids yet.</p>";
      return;
    }

    myBidsList.innerHTML = bids
      .map(
        (bid) => `
        <div class="item-row">
          <div class="item-row-head">
            <div>
              <strong>${escapeHtml(bid.gig_title)}</strong>
              <div class="item-meta">Your bid: ${formatCurrency(bid.bid_amount)} (Budget: ${formatCurrency(bid.budget)})</div>
            </div>
            ${badge(bid.status)}
          </div>
        </div>`
      )
      .join("");
  } catch (error) {
    myBidsList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

// ---------------------------------------------------------
// MY CONTRACTS (submit work / view fraud score)
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

        if (contract.contract_status === "ACTIVE" && contract.escrow_status === "HELD") {
          actionButton = `<button class="btn-small submit-work-btn" data-contract-id="${contract.contract_id}">Submit Work</button>`;
        }

        return `
        <div class="item-row">
          <div class="item-row-head">
            <div>
              <strong>${escapeHtml(contract.gig_title)}</strong>
              <div class="item-meta">
                Client: ${escapeHtml(contract.client_name)} &middot;
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

    document.querySelectorAll(".submit-work-btn").forEach((btn) => {
      btn.addEventListener("click", () => submitWork(btn.dataset.contractId));
    });
    document.querySelectorAll(".fraud-btn").forEach((btn) => {
      btn.addEventListener("click", () => toggleFraudScore(btn.dataset.contractId));
    });
  } catch (error) {
    myContractsList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

async function submitWork(contractId) {
  const errorBox = document.getElementById(`contract-error-${contractId}`);
  errorBox.textContent = "";

  try {
    await authFetch(`/contracts/${contractId}/submit-work`, { method: "POST" });
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

loadOpenGigs();
loadMyBids();
loadMyContracts();


// ---------------------------------------------------------
// LIVE STAT CARDS (replaces the placeholder demo numbers)
// ---------------------------------------------------------

function setStatCard(label, value, caption) {
  const labelEl = Array.from(document.querySelectorAll("body *")).find(
    (el) => el.children.length === 0 && el.textContent.trim() === label &&
            el.nextElementSibling && el.nextElementSibling.nextElementSibling &&
            /demo data|unavailable|live/i.test(el.nextElementSibling.nextElementSibling.textContent)
  );
  if (!labelEl) return;
  const valueEl = labelEl.nextElementSibling;
  const captionEl = valueEl.nextElementSibling;
  valueEl.textContent = value;
  captionEl.textContent = caption;
}

async function updateStats() {
  try {
    const [bids, contracts] = await Promise.all([
      authFetch("/bids/mine"),
      authFetch("/contracts/mine"),
    ]);

    const activeBids = bids.filter((b) => b.status === "PENDING").length;
    const held = contracts
      .filter((c) => c.escrow_status === "HELD")
      .reduce((sum, c) => sum + Number(c.agreed_amount || 0), 0);
    const completed = contracts.filter((c) => c.contract_status === "COMPLETED").length;

    setStatCard("Active Bids", activeBids, "Pending bids");
    setStatCard("Contracts", contracts.length, "All contracts");
    setStatCard("Pending", formatCurrency(held), "Held in escrow");
    setStatCard("Completed", completed, "Contracts finished");
  } catch (error) {
    ["Active Bids", "Contracts", "Pending", "Completed"].forEach((l) =>
      setStatCard(l, "-", "Unavailable")
    );
  }
}

updateStats();
setInterval(updateStats, 15000);


// ---------------------------------------------------------
// LIVE STAT CARDS
// ---------------------------------------------------------
const STAT_LABELS = ["Active Bids", "Contracts", "Pending", "Completed"];

function findStatCards() {
  const cards = {};
  document.querySelectorAll("body *").forEach((el) => {
    if (el.children.length === 0 && /^(demo data|unavailable|loading)/i.test(el.textContent.trim()) || el.dataset.stat) {
      const card = el.parentElement;
      const valueEl = el.previousElementSibling;
      if (!card || !valueEl) return;
      const label = el.dataset.stat || STAT_LABELS.find((l) => card.textContent.trim().startsWith(l));
      if (label) {
        el.dataset.stat = label;
        cards[label] = { valueEl, captionEl: el };
      }
    }
  });
  return cards;
}

function setStat(cards, label, value, caption) {
  if (!cards[label]) return;
  cards[label].valueEl.textContent = value;
  cards[label].captionEl.textContent = caption;
}

async function updateStats() {
  const cards = findStatCards();
  try {
    const [bids, contracts] = await Promise.all([authFetch("/bids/mine"), authFetch("/contracts/mine")]);
    const held = contracts
      .filter((c) => c.escrow_status === "HELD")
      .reduce((sum, c) => sum + Number(c.agreed_amount || 0), 0);
    setStat(cards, "Active Bids", bids.filter((b) => b.status === "PENDING").length, "Pending bids");
    setStat(cards, "Contracts", contracts.length, "All contracts");
    setStat(cards, "Pending", formatCurrency(held), "Held in escrow");
    setStat(cards, "Completed", contracts.filter((c) => c.contract_status === "COMPLETED").length, "Contracts finished");
  } catch (error) {
    STAT_LABELS.forEach((l) => setStat(cards, l, "-", "Unavailable"));
  }
}

updateStats();
setInterval(updateStats, 15000);
