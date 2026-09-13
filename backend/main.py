from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database import get_db_connection
from backend.auth_dependency import get_current_user
from backend.services import marketplace
from agent.resource_manager import make_resource_decision

from telemetry.telemetry_client import (
    test_cassandra_connection,
    insert_telemetry,
    get_recent_telemetry,
)

from mongo.activity_logs import (
    log_activity,
    test_mongo_connection,
)

from mongo.auth_users import (
    register_account,
    login_account,
)

from backend.services.blockchain import (
    add_transaction_to_ledger,
    verify_ledger,
)


app = FastAPI(
    title="GigTrust API",
    description="Cloud-based freelance marketplace with secure escrow transactions",
    version="1.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str


class LoginRequest(BaseModel):
    email: str
    password: str
    role: str


class CreateGigRequest(BaseModel):
    title: str
    description: str
    budget: float


class PlaceBidRequest(BaseModel):
    bid_amount: float
    proposal: str


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def require_role(current_user: dict, expected_role: str):
    if current_user["role"].upper() != expected_role:
        raise HTTPException(status_code=403, detail=f"This action requires a {expected_role} account.")


@app.get("/")
def home():
    return {
        "project": "GigTrust",
        "message": "Backend running successfully",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

@app.post("/auth/register")
def register(request: RegisterRequest):
    try:
        return register_account(
            name=request.name,
            email=request.email,
            password=request.password,
            role=request.role,
        )
    except Exception as e:
        return {
            "status": "failed",
            "message": "Account registration failed.",
            "error": str(e),
        }


@app.post("/auth/login")
def login(request: LoginRequest):
    try:
        return login_account(
            email=request.email,
            password=request.password,
            role=request.role,
        )
    except Exception as e:
        return {
            "status": "failed",
            "message": "Login failed.",
            "error": str(e),
        }


@app.get("/auth/me")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "message": "Token is valid.",
        "user": current_user,
    }


# ---------------------------------------------------------
# MARKETPLACE: GIGS
# ---------------------------------------------------------

@app.post("/gigs")
def post_gig(request: CreateGigRequest, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "CLIENT")
    return marketplace.create_gig(
        client_sql_id=int(current_user["sub"]),
        title=request.title,
        description=request.description,
        budget=request.budget,
    )


@app.get("/gigs")
def get_open_gigs():
    return marketplace.list_open_gigs()


@app.get("/gigs/{gig_id}")
def get_gig_detail(gig_id: int):
    return marketplace.get_gig(gig_id)


# ---------------------------------------------------------
# MARKETPLACE: BIDS
# ---------------------------------------------------------

@app.post("/gigs/{gig_id}/bids")
def post_bid(gig_id: int, request: PlaceBidRequest, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "FREELANCER")
    return marketplace.place_bid(
        gig_id=gig_id,
        freelancer_sql_id=int(current_user["sub"]),
        bid_amount=request.bid_amount,
        proposal=request.proposal,
    )


@app.get("/gigs/{gig_id}/bids")
def get_bids(gig_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "CLIENT")
    return marketplace.list_bids_for_gig(
        gig_id=gig_id,
        requesting_client_sql_id=int(current_user["sub"]),
    )


@app.post("/bids/{bid_id}/accept")
def accept_a_bid(bid_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "CLIENT")
    return marketplace.accept_bid(
        bid_id=bid_id,
        requesting_client_sql_id=int(current_user["sub"]),
    )


# ---------------------------------------------------------
# MARKETPLACE: CONTRACTS + ESCROW
# ---------------------------------------------------------

@app.post("/contracts/{contract_id}/fund-escrow")
def fund_contract_escrow(contract_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "CLIENT")
    return marketplace.fund_escrow(
        contract_id=contract_id,
        requesting_client_sql_id=int(current_user["sub"]),
    )


@app.post("/contracts/{contract_id}/submit-work")
def submit_contract_work(contract_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "FREELANCER")
    return marketplace.submit_work(
        contract_id=contract_id,
        requesting_freelancer_sql_id=int(current_user["sub"]),
    )


@app.post("/contracts/{contract_id}/approve")
def approve_contract_completion(contract_id: int, current_user: dict = Depends(get_current_user)):
    require_role(current_user, "CLIENT")
    return marketplace.approve_and_release(
        contract_id=contract_id,
        requesting_client_sql_id=int(current_user["sub"]),
    )


# ---------------------------------------------------------
# DATABASE HEALTH
# ---------------------------------------------------------

@app.get("/health/database")
def database_health():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT 1")
        result = cursor.fetchone()

        cursor.close()
        connection.close()

        return {
            "database": "Azure SQL",
            "status": "connected",
            "test": result[0],
        }

    except Exception as e:
        return {
            "database": "Azure SQL",
            "status": "failed",
            "error": str(e),
        }


# ---------------------------------------------------------
# BLOCKCHAIN LEDGER
# ---------------------------------------------------------

@app.post("/ledger/add/{transaction_id}")
def add_ledger_block(transaction_id: int):
    try:
        return add_transaction_to_ledger(transaction_id)
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/ledger/verify")
def verify_blockchain_ledger():
    try:
        return verify_ledger()
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ---------------------------------------------------------
# MONGODB
# ---------------------------------------------------------

@app.post("/activity/test")
def test_activity_log():
    try:
        return log_activity(
            event_type="TEST_EVENT",
            user_id=1,
            details={
                "message": "GigTrust MongoDB activity logging test",
            },
        )
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/health/mongodb")
def mongodb_health():
    try:
        return test_mongo_connection()
    except Exception as e:
        return {
            "database": "Cosmos DB MongoDB",
            "status": "failed",
            "error": str(e),
        }


@app.post("/activity/escrow-funded")
def log_escrow_funded():
    try:
        return log_activity(
            event_type="ESCROW_FUNDED",
            user_id=1,
            transaction_id=1,
            amount=9500.00,
            details={
                "escrow_id": 1,
                "contract_id": 1,
                "source": "Azure SQL",
            },
        )
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# ---------------------------------------------------------
# CASSANDRA
# ---------------------------------------------------------

@app.get("/health/cassandra")
def cassandra_health():
    try:
        return test_cassandra_connection()
    except Exception as e:
        return {
            "database": "Cosmos DB Cassandra",
            "status": "failed",
            "error": str(e),
        }


# ---------------------------------------------------------
# TELEMETRY
# ---------------------------------------------------------

@app.post("/telemetry/test")
def create_test_telemetry():
    try:
        results = []

        results.append(
            insert_telemetry(
                region="Central India",
                metric_type="CPU_UTIL",
                node_id="gigtrust-api-01",
                value=72.4,
            )
        )

        results.append(
            insert_telemetry(
                region="Central India",
                metric_type="LATENCY_MS",
                node_id="gigtrust-api-01",
                value=118.0,
            )
        )

        results.append(
            insert_telemetry(
                region="Central India",
                metric_type="THROUGHPUT_RPS",
                node_id="gigtrust-api-01",
                value=430.0,
            )
        )

        return {
            "status": "success",
            "scenario": "normal_load",
            "region": "Central India",
            "telemetry": results,
        }

    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/telemetry/{region}/{metric_type}")
def read_telemetry(region: str, metric_type: str):
    try:
        return get_recent_telemetry(
            region=region,
            metric_type=metric_type,
        )
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.get("/agent/decision/{region}")
def resource_agent_decision(region: str):
    try:
        return make_resource_decision(region)
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.post("/telemetry/high-load")
def create_high_load_telemetry():
    try:
        results = []

        results.append(
            insert_telemetry(
                region="Central India",
                metric_type="CPU_UTIL",
                node_id="gigtrust-api-01",
                value=88.5,
            )
        )

        results.append(
            insert_telemetry(
                region="Central India",
                metric_type="LATENCY_MS",
                node_id="gigtrust-api-01",
                value=220.0,
            )
        )

        results.append(
            insert_telemetry(
                region="Central India",
                metric_type="THROUGHPUT_RPS",
                node_id="gigtrust-api-01",
                value=910.0,
            )
        )

        return {
            "status": "success",
            "scenario": "high_load",
            "region": "Central India",
            "telemetry": results,
        }

    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.post("/telemetry/second-region")
def create_second_region_telemetry():
    try:
        results = []

        results.append(
            insert_telemetry(
                region="Korea Central",
                metric_type="CPU_UTIL",
                node_id="gigtrust-api-02",
                value=42.0,
            )
        )

        results.append(
            insert_telemetry(
                region="Korea Central",
                metric_type="LATENCY_MS",
                node_id="gigtrust-api-02",
                value=85.0,
            )
        )

        results.append(
            insert_telemetry(
                region="Korea Central",
                metric_type="THROUGHPUT_RPS",
                node_id="gigtrust-api-02",
                value=310.0,
            )
        )

        return {
            "status": "success",
            "region": "Korea Central",
            "telemetry": results,
        }

    except Exception as e:
        return {"status": "failed", "error": str(e)}
