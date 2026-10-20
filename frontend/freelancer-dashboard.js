// Requires dashboard-common.js to already be loaded (authFetch, formatCurrency, escapeHtml).

const browseGigsList = document.getElementById("browseGigsList");
const myBidsList = document.getElementById("myBidsList");
const myContractsList = document.getElementById("myContractsList");

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
const STATS_REFRESH_MS = 15000;
const STAT_LABELS = ["Active Bids", "Contracts", "Pending", "Completed"];

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
  return `<span class="badge ${statusBadgeClass(status)}">${escapeHtml(String(status))}</span>`;
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

    document.querySelectorAll(".bid-toggle-btn").forEach((toggleButton) => {
      toggleButton.addEventListener("click", () => {
        document.getElementById(`bid-form-${toggleButton.dataset.gigId}`).classList.toggle("hidden");
      });
    });

    document.querySelectorAll(".bid-form").forEach((bidForm) => {
      bidForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const gigId = bidForm.dataset.gigId;
        const errorBox = document.getElementById(`bid-error-${gigId}`);
        const successBox = document.getElementById(`bid-success-${gigId}`);
        const submitButton = bidForm.querySelector("button[type='submit']");
        errorBox.textContent = "";
        successBox.textContent = "";

        const bidAmount = parseFloat(bidForm.querySelector(".bid-amount-input").value);
        const proposal = bidForm.querySelector(".bid-proposal-input").value.trim();

        if (Number.isNaN(bidAmount) || bidAmount <= 0) {
          errorBox.textContent = "Enter a valid bid amount.";
          return;
        }
        if (!proposal) {
          errorBox.textContent = "Proposal cannot be empty.";
          return;
        }

        submitButton.disabled = true;
        try {
          await authFetch(`/gigs/${gigId}/bids`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bid_amount: bidAmount, proposal }),
          });

          successBox.textContent = "Bid submitted successfully.";
          bidForm.reset();
          loadMyBids();
          updateStats();
        } catch (error) {
          errorBox.textContent = error.message;
        } finally {
          submitButton.disabled = false;
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
// MY CONTRACTS (upload deliverable / submit work / fraud score)
// ---------------------------------------------------------

function buildDeliverableSection(contract) {
  const isActive = contract.contract_status === "ACTIVE";
  const isFunded = contract.escrow_status === "HELD";

  if (isActive && isFunded) {
    return `
      <div class="deliver-box">
        <input type="file" id="file-${contract.contract_id}" />
        <input type="text" id="note-${contract.contract_id}" placeholder="Note to client (optional)" />
        <button class="btn-small submit-work-btn" data-contract-id="${contract.contract_id}">Upload and Submit Work</button>
        <div class="inline-success upload-status" id="upload-status-${contract.contract_id}"></div>
      </div>`;
  }

  if (isActive && !isFunded) {
    return "<p class='muted'>Upload is available once the client funds the escrow.</p>";
  }

  if (contract.contract_status === "WORK_SUBMITTED") {
    return "<p class='muted'>Work submitted. Waiting for client review.</p>";
  }

  return "";
}

async function loadMyContracts() {
  myContractsList.innerHTML = "<p class='muted'>Loading...</p>";

  try {
    const contracts = await authFetch("/contracts/mine");

    if (contracts.length === 0) {
      myContractsList.innerHTML = "<p class='muted'>No contracts yet.</p>";
      return;
    }

    myContractsList.innerHTML = contracts
      .map(
        (contract) => `
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
          ${buildDeliverableSection(contract)}
          <button class="btn-small secondary fraud-btn" data-contract-id="${contract.contract_id}">View Fraud Score</button>
          <div class="inline-error contract-error" id="contract-error-${contract.contract_id}"></div>
          <div class="fraud-box hidden" id="fraud-box-${contract.contract_id}"></div>
        </div>`
      )
      .join("");

    document.querySelectorAll(".submit-work-btn").forEach((submitButton) => {
      submitButton.addEventListener("click", () => submitWork(submitButton.dataset.contractId));
    });
    document.querySelectorAll(".fraud-btn").forEach((fraudButton) => {
      fraudButton.addEventListener("click", () => toggleFraudScore(fraudButton.dataset.contractId));
    });
  } catch (error) {
    myContractsList.innerHTML = `<p class="inline-error">${escapeHtml(error.message)}</p>`;
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(new Error("Could not read the file."));
    reader.readAsDataURL(file);
  });
}

async function submitWork(contractId) {
  const errorBox = document.getElementById(`contract-error-${contractId}`);
  const statusBox = document.getElementById(`upload-status-${contractId}`);
  const submitButton = document.querySelector(`.submit-work-btn[data-contract-id="${contractId}"]`);
  const fileInput = document.getElementById(`file-${contractId}`);
  const noteInput = document.getElementById(`note-${contractId}`);

  errorBox.textContent = "";
  statusBox.textContent = "";

  const file = fileInput.files[0];
  const note = noteInput.value.trim();

  if (!file) {
    errorBox.textContent = "Please attach your completed work.";
    return;
  }
  if (file.size > MAX_FILE_SIZE_BYTES) {
    errorBox.textContent = "File is larger than 5 MB.";
    return;
  }

  submitButton.disabled = true;
  try {
    statusBox.textContent = "Uploading...";
    const data_base64 = await fileToBase64(file);

    await authFetch(`/contracts/${contractId}/deliverable`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        file_name: file.name,
        content_type: file.type || "application/octet-stream",
        data_base64,
        note,
      }),
    });

    statusBox.textContent = "Uploaded. Submitting work...";
    await authFetch(`/contracts/${contractId}/submit-work`, { method: "POST" });

    loadMyContracts();
    updateStats();
  } catch (error) {
    statusBox.textContent = "";
    errorBox.textContent = error.message;
    submitButton.disabled = false;
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
    const reasons = Array.isArray(score.reasons) ? score.reasons : [];
    box.innerHTML = `
      <strong>Risk: ${escapeHtml(String(score.risk_tier))} (${escapeHtml(String(score.risk_score))} pts)</strong>
      <ul>${reasons.map((reason) => `<li>${escapeHtml(String(reason))}</li>`).join("")}</ul>
    `;
  } catch (error) {
    box.innerHTML = `<span class="inline-error">${escapeHtml(error.message)}</span>`;
  }
}

// ---------------------------------------------------------
// LIVE STAT CARDS
// ---------------------------------------------------------

// Finds each stat card once, by locating the placeholder caption
// ("Demo data" / "Unavailable" / "Loading") under each label.
function findStatCards() {
  const cards = {};

  document.querySelectorAll("body *").forEach((element) => {
    const isLeaf = element.children.length === 0;
    const isPlaceholderCaption = /^(demo data|unavailable|loading)/i.test(element.textContent.trim());
    if (!isLeaf || !isPlaceholderCaption) return;

    const card = element.parentElement;
    const valueElement = element.previousElementSibling;
    if (!card || !valueElement) return;

    const cardText = card.textContent.trim();
    const label = STAT_LABELS.find((statLabel) => cardText.startsWith(statLabel));
    if (label) {
      cards[label] = { valueElement, captionElement: element };
    }
  });

  return cards;
}

const statCards = findStatCards();

function setStat(label, value, caption) {
  const card = statCards[label];
  if (!card) return;
  card.valueElement.textContent = value;
  card.captionElement.textContent = caption;
}

async function updateStats() {
  try {
    const [bids, contracts] = await Promise.all([
      authFetch("/bids/mine"),
      authFetch("/contracts/mine"),
    ]);

    const pendingBidCount = bids.filter((bid) => bid.status === "PENDING").length;
    const heldAmount = contracts
      .filter((contract) => contract.escrow_status === "HELD")
      .reduce((sum, contract) => sum + Number(contract.agreed_amount || 0), 0);
    const completedCount = contracts.filter((contract) => contract.contract_status === "COMPLETED").length;

    setStat("Active Bids", pendingBidCount, "Pending bids");
    setStat("Contracts", contracts.length, "All contracts");
    setStat("Pending", formatCurrency(heldAmount), "Held in escrow");
    setStat("Completed", completedCount, "Contracts finished");
  } catch (error) {
    STAT_LABELS.forEach((label) => setStat(label, "-", "Unavailable"));
  }
}

// ---------------------------------------------------------
// INITIAL LOAD
// ---------------------------------------------------------

loadOpenGigs();
loadMyBids();
loadMyContracts();
updateStats();
setInterval(updateStats, STATS_REFRESH_MS);