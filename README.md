# GigTrust

**GigTrust** is a cloud native freelance marketplace built for a combined **Database Management Systems (DBMS)** and **Cloud Computing** course at Amrita Vishwa Vidyapeetham. It combines transaction safe escrow, polyglot persistence, explainable fraud scoring, a tamper evident ledger, a lightweight digital twin, and a two region Azure deployment with automatic failover.

The DBMS side covers ACID transactions, normalisation, concurrency control and deadlocks, escrow workflows, activity logging and telemetry storage. The cloud side covers Docker, Azure Container Registry, Azure Container Apps, Azure App Service, Azure Traffic Manager, Azure Key Vault, health probes and failover.

---

## 1. Architecture

```text
                  Users (Client / Freelancer / Admin)
                                |
                                v
                    Azure Traffic Manager (Priority)
                      Priority 1: Central India
                      Priority 2: Korea Central
                    /                         \
                   v                           v
   Central India                        Korea Central
   Azure Container Apps (Express)       Azure App Service (Free F1)
   FastAPI backend + frontend           FastAPI backend + frontend
                   \                           /
                    v                         v
        +----------------+  +----------------+  +----------------+
        | Azure SQL      |  | Cosmos DB      |  | Cosmos DB      |
        | transactions   |  | MongoDB        |  | Cassandra      |
        | escrow, ledger |  | accounts, logs |  | telemetry      |
        +----------------+  +----------------+  +----------------+

   Azure Container Registry: one image, pulled by both regions
   Azure Key Vault: 13 settings, copied into each app as environment variables
```

Both regions run the **same Docker image** and use the **same data stores** in Central India.

| Component | Technology | Purpose |
|---|---|---|
| Backend | FastAPI (Python 3.11) | REST API and static frontend hosting |
| Frontend | HTML, CSS, JavaScript | Role dashboards, served at `/app/index.html` |
| Relational database | Azure SQL Database | Users, Gigs, Bids, Contracts, Escrows, Transactions, LedgerBlocks |
| Document database | Cosmos DB for MongoDB | Login accounts and activity logs |
| Wide column database | Cosmos DB for Cassandra | Telemetry and agent decisions |
| Secrets | Azure Key Vault | 13 application settings (RBAC) |
| Registry | Azure Container Registry | Docker image storage |
| Primary compute | Azure Container Apps (Express) | Central India |
| Secondary compute | Azure App Service (Free F1) | Korea Central |
| Global routing | Azure Traffic Manager | Priority routing, HTTPS probe on `/health` |

---

## 2. Features

- **Marketplace flow:** post gig, bid, accept, fund escrow, submit work, approve and release. Every step is one SQL transaction with role and ownership checks.
- **Authentication:** PBKDF2 SHA256 password hashes (200,000 iterations) stored in MongoDB, and 24 hour JWT tokens whose subject is the SQL user id. Roles are CLIENT, FREELANCER and ADMIN.
- **Explainable fraud scoring:** preventive scoring when a bid is accepted and audit scoring on contracts. Each point comes from a named rule with a plain language reason.
- **Hash chained ledger:** each block stores the hash of the previous block. It is tamper evident, not a distributed blockchain.
- **Telemetry agent:** recommends SCALE_UP, SCALE_DOWN, REROUTE or NO_ACTION from Cassandra telemetry and logs every decision.
- **Digital twin (lightweight):** mirrors the latest telemetry of each region and simulates a load change. It is an analytic approximation, not a validated simulation.
- **Role dashboards:** client, freelancer and admin pages with live data and live health indicators.

---

## 3. Fraud scoring

| Rule | Condition | Points |
|---|---|---|
| Lowball bid | bid below 30% of budget | 30 |
| Overbid | bid above 150% of budget | 15 |
| Fast release (audit only) | escrow funded and released in under 300 s | 25 |
| New account | freelancer account under 24 hours old | 20 |
| Spam bidding (preventive only) | more than 5 bids in 60 minutes | 20 |
| Large amount | 50,000 or more | 10 |

Tiers: LOW below 25, MEDIUM 25 to 49, HIGH 50 to 74, CRITICAL 75 or more. A CRITICAL preventive score blocks bid acceptance. Every decision is logged to MongoDB. The weights are hand chosen, not calibrated on data.

`evaluate_fraud.py` runs an offline evaluation on 90 labelled synthetic cases and prints a confusion matrix, precision, recall and F1 at thresholds 25, 50 and 75.

---

## 4. Database design

### Azure SQL Database

The schema is normalised to third normal form. Key constraints:

- `Users.role` is restricted by a CHECK constraint (CLIENT, FREELANCER, ADMIN).
- `Bids` has UNIQUE on (gig, freelancer), so one bid per gig per freelancer.
- `Contracts` has UNIQUE on gig, so at most one contract per gig.
- `Escrows` records `funded_at` and `released_at`.
- `Transactions` records ESCROW_FUND, ESCROW_RELEASE and ESCROW_REFUND events.
- `LedgerBlocks` stores the hash chain.

**ACID in practice:** escrow funding updates the balance, the escrow status and the transaction record as one unit. Bid acceptance accepts one bid, rejects the others, moves the gig to in progress and creates the contract and escrow in one transaction. Any failure rolls back everything.

**Concurrency and deadlocks:** `database/deadlock_demo.sql` is run in two parallel sessions to create a deadlock, show detection and rollback, and show consistent lock ordering as prevention.

### Cosmos DB for MongoDB

- `users`: account documents with the PBKDF2 hash and the `sql_user_id` that links to the SQL row.
- `activity_logs`: append only event documents, including fraud decisions and digital twin simulations.

### Cosmos DB for Cassandra

Create these once in the `gigtrust` keyspace (Data Explorer, Add Table):

```sql
CREATE TABLE telemetry_readings (
    region TEXT, metric_type TEXT, ts TIMESTAMP, node_id TEXT, value DOUBLE,
    PRIMARY KEY ((region, metric_type), ts, node_id)
) WITH CLUSTERING ORDER BY (ts DESC, node_id ASC);

CREATE TABLE scaling_actions (
    region TEXT, ts TIMESTAMP, action TEXT, trigger_metric TEXT,
    trigger_value DOUBLE, threshold DOUBLE,
    PRIMARY KEY (region, ts)
) WITH CLUSTERING ORDER BY (ts DESC);
```

Seed demo telemetry with `POST /telemetry/high-load` and `POST /telemetry/second-region`.

---

## 5. API routes

| Area | Routes |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Gigs | `POST /gigs`, `GET /gigs`, `GET /gigs/mine`, `GET /gigs/{id}` |
| Bids | `POST /gigs/{id}/bids`, `GET /gigs/{id}/bids`, `GET /bids/mine`, `POST /bids/{id}/accept` |
| Contracts | `GET /contracts/mine`, `POST /contracts/{id}/fund-escrow`, `POST /contracts/{id}/submit-work`, `POST /contracts/{id}/approve` |
| Fraud | `GET /fraud/score/contract/{id}` |
| Ledger | `POST /ledger/add/{transaction_id}`, `GET /ledger/verify` |
| Telemetry and agent | `POST /telemetry/high-load`, `POST /telemetry/second-region`, `GET /telemetry/{region}/{metric_type}`, `GET /agent/decision/{region}` |
| Digital twin | `GET /twin/state`, `POST /twin/simulate` |
| Admin | `GET /admin/users`, `GET /admin/gigs`, `GET /admin/transactions` |
| Health | `/health`, `/health/database`, `/health/mongodb`, `/health/cassandra` |

Interactive documentation is at `/docs`. Static routes such as `/gigs/mine` must be declared before `/gigs/{gig_id}`, otherwise FastAPI tries to read "mine" as an integer and returns a 422.

### Digital twin example

```json
POST /twin/simulate
{ "region": "Central India", "load_multiplier": 3, "replicas": 1 }
```

Leave out `cpu`, `latency_ms` and `throughput_rps` unless you want to override the live telemetry.

---

## 6. Secrets and configuration

All settings live in **Azure Key Vault** (`gigtrust-kv-24262`, RBAC model) as 13 secrets with hyphenated names (for example `SQL-PASSWORD`). `backend/keyvault_loader.py` copies them into environment variables with underscored names (`SQL_PASSWORD`).

- **Locally:** the backend signs in to Azure in the browser at startup and loads all 13. The loader must be the first import in `backend/main.py`. Modules read settings **when a function is called**, not at import time.
- **In the cloud:** the Express Container Apps environment does not support managed identity, so the settings are copied from Key Vault into the apps. Sensitive values are stored as Container Apps secrets and referenced by name. If all 13 variables are already set, the loader skips Key Vault.
- **Never commit secrets.** `.env` may hold only non sensitive values and must stay in `.gitignore`.
- Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` to your own values. The built in defaults are for demonstration only.

---

## 7. Run locally

1. Install Python 3.11 and the Microsoft ODBC Driver 18 for SQL Server.
2. Create and activate a virtual environment, then install packages:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Start the backend and sign in to Azure once in the browser tab that opens:

```powershell
uvicorn backend.main:app
```

4. Wait for `[Key Vault] Loaded 13/13 secrets successfully.`, then open `http://127.0.0.1:8000/app/index.html`.

Local runs connect to Cosmos MongoDB on port 10255. Some networks (college Wi-Fi, VPNs, antivirus firewalls) block that port, which makes login fail locally even though the cloud app works.

---

## 8. Docker and deployment

```powershell
docker build -t <registry>.azurecr.io/gigtrust-api:<tag> .
docker login <registry>.azurecr.io
docker push <registry>.azurecr.io/gigtrust-api:<tag>
```

Use a **new tag each time** (`v2`, `v3`, ...). Container Apps does not always pull again when the tag is unchanged.

```bash
# India (Cloud Shell)
az containerapp update -n gigtrust-api-india -g gigtrust-rg --image <registry>.azurecr.io/gigtrust-api:<tag>
# Korea
az webapp restart -n gigtrust-api-korea-24262 -g gigtrust-rg
```

The Dockerfile uses `python:3.11-slim-bookworm`, installs `msodbcsql18` and runs uvicorn on port 8000.

### Live endpoints (while the resources are running)

| Region | URL |
|---|---|
| Central India | `https://gigtrust-api-india.bluebush-c9d606d0.centralindia.azurecontainerapps.io/app/index.html` |
| Korea Central | `https://gigtrust-api-korea-24262-edc5eue3gnf5dxfv.koreacentral-01.azurewebsites.net/app/index.html` |

### Pause and resume (to save credit)

```bash
# Pause
az containerapp update -n gigtrust-api-india -g gigtrust-rg --min-replicas 0 --max-replicas 1
az webapp stop -n gigtrust-api-korea-24262 -g gigtrust-rg
az network traffic-manager profile update -g gigtrust-rg -n gigtrust-tm-24262 --status Disabled

# Resume
az webapp start -n gigtrust-api-korea-24262 -g gigtrust-rg
az network traffic-manager profile update -g gigtrust-rg -n gigtrust-tm-24262 --status Enabled
az containerapp update -n gigtrust-api-india -g gigtrust-rg --min-replicas 1 --max-replicas 1
```

---

## 9. Multi region failover

Traffic Manager uses **priority routing**: Central India is returned while healthy, otherwise Korea Central.

| Setting | Value |
|---|---|
| Probe | HTTPS, port 443, path `/health` |
| Interval | 10 s |
| Tolerated failures | 1 |
| Timeout | 9 s |
| DNS TTL | 60 s |

Check which region is served:

```powershell
Resolve-DnsName gigtrust-tm-24262.trafficmanager.net
```

**Test:** disable the `india` endpoint, resolve again (Korea Central should answer), then re-enable it (India should return). Measured: **8 s to fail over and 8 s to fail back** when the endpoint is disabled by an administrator. An unplanned crash would take longer, up to roughly I x (N + 1) + TTL = 80 s.

Traffic Manager is DNS based, not a reverse proxy. Its hostname returns a backend hostname whose TLS certificate belongs to that backend, so browsers show a certificate warning on the Traffic Manager name. Use the regional URLs for browsing and the Traffic Manager name for DNS failover evidence.

---

## 10. Results

- **Functional:** all four health routes passed in both regions. The full gig lifecycle ran on the deployed system (post, bid, accept, fund, submit, approve).
- **Fraud scorer (90 synthetic cases):** the audit scorer reached F1 0.83 at the HIGH threshold with no false positives. The preventive scorer reached F1 0.79 at threshold 25.
- **Real fraud cases:** a bid of 5,000 on a 60,000 budget from a new account scored 50 (HIGH). A contract released after 51 seconds scored 45 (MEDIUM).
- **Latency (from India, medians):** `/health` 560 ms in India and 129 ms in Korea. Database routes in Korea were 1.8 times (SQL), 3.0 times (MongoDB) and 5.1 times (Cassandra) slower, because all data stores stay in Central India.
- **Digital twin:** with seeded telemetry (India 88.5% CPU and 220 ms, Korea 42% and 85 ms), a load multiplier of 1 recommended REROUTE and predicted India at 44.2% and Korea at 86.2%. At a multiplier of 3, both regions saturated at 100%.
- **Ledger:** 5 blocks verified as valid on the deployed system.
- **Cost:** about 330 INR so far on Azure for Students.

---

## 11. Azure for Students limitations

- Only some regions are allowed (Central India, Korea Central, Malaysia West, Indonesia Central and Austria East were observed).
- Only one Container Apps environment is allowed, so Korea Central uses App Service for Containers.
- Azure Front Door cannot be created on a student subscription, so Traffic Manager is used.
- The Express Container Apps environment does not support managed identity, Restart, revision suffixes or the log stream CLI.
- Free tier App Service has a daily compute quota and no Always On.

---

## 12. Troubleshooting lessons

| Problem | Cause and fix |
|---|---|
| `asyncore` import error | The Cassandra driver needs Python 3.11. It fails on 3.12 and later. |
| Settings are `None` | A module read the environment at import time. Read settings inside functions and import the Key Vault loader first. |
| `localhost:27017` Mongo error | Same cause: an empty `MONGO_URI` makes pymongo fall back to localhost. |
| `Invalid key` after key rotation | Update the Key Vault secret, copy it into the Container App secret, and force a new revision. |
| `/app` returns Not Found | The Container App kept the old image. Push a new tag and update the app. |
| `unauthorized` on `docker push` | Log in to the registry again with the current admin password. |
| Cassandra `table does not exist` | Create `telemetry_readings` and `scaling_actions` (section 4). |
| Login returns 200 but nothing happens | The API returns `status: failed` inside a 200. Read the response body. |
| Azure SQL timeouts after idle | Free tier cold start. `database.py` retries 3 times with a 2 second gap. |
| `/gigs/mine` returns 422 | Declare static routes before `/gigs/{gig_id}`. |

---

## 13. Known limitations

- Both regions share one set of data stores, so there is no data replication.
- Secrets are injected as configuration on Express, not fetched through a managed identity.
- The CRITICAL fraud gate is almost unreachable at bid acceptance: the best realistic combination scores 70 points.
- Fraud weights are heuristic and were tested only on synthetic cases written by the authors.
- The digital twin is an analytic model evaluated on seeded telemetry.
- The telemetry agent recommends actions and does not change Azure resources.
- Client balances are topped up by a direct database update, since no payment gateway is in scope.
- The SQL firewall allows all addresses for demonstration.

## 14. Future work

Geo replication (Azure SQL failover groups, multi region Cosmos DB), managed identity on a standard Container Apps environment, Azure Front Door with a custom domain, a wallet deposit endpoint, a dispute workflow, calibrating fraud weights on real data, an explainable learned model, anchoring the ledger to an independent store, and validating the digital twin against measured load.

---

## 15. Suggested demo flow

1. Show the architecture and the resource group in the portal.
2. Open the four health routes in both regions.
3. Run the marketplace flow as Alice (client) and Bob (freelancer): post, bid, accept (show the fraud score), fund, submit, approve.
4. Place a lowball bid and show the MEDIUM score and its reason.
5. Run `evaluate_fraud.py` and show the metrics.
6. Call `/ledger/verify`.
7. Seed telemetry, open `/twin/state` and run `/twin/simulate` with multipliers 1 and 3.
8. Run the failover test: India, Korea, India.
9. State the limitations.

---

## 16. Credits

The relational schema, telemetry client, resource management agent, ledger service and the original multi region design come from the course codebase by **Jignesh Sudheer, Devana Madhavan and Iniya M**. **Rupanshi Sangwan** added authentication, escrow workflows, fraud scoring and its evaluation, Key Vault integration, the cloud deployment and failover measurements, the digital twin and the live frontend.

## 17. Licence

All rights reserved. See `LICENSE`.