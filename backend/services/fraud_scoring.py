from datetime import datetime, timezone
from fastapi import HTTPException

from backend.database import get_db_connection
from mongo.activity_logs import log_activity


# ---------------------------------------------------------
# RULE THRESHOLDS
# (Kept as named constants, same style as agent/resource_manager.py,
# so every threshold is easy to find, justify, and tune.)
# ---------------------------------------------------------

LOWBALL_BID_RATIO = 0.30          # bid < 30% of gig budget
OVERBID_RATIO = 1.50              # bid > 150% of gig budget
FAST_RELEASE_SECONDS = 300        # escrow funded -> released in under 5 minutes
NEW_ACCOUNT_HOURS = 24            # freelancer account created < 24h before bidding
LARGE_TRANSACTION_AMOUNT = 50000  # flagged for review regardless of other factors

RISK_TIERS = [
    (75, "CRITICAL"),
    (50, "HIGH"),
    (25, "MEDIUM"),
    (0, "LOW"),
]


def _tier_for_score(score: int) -> str:
    for threshold, tier in RISK_TIERS:
        if score >= threshold:
            return tier
    return "LOW"


def _get_contract_context(contract_id: int) -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT
                c.contract_id,
                c.gig_id,
                c.client_id,
                c.freelancer_id,
                c.agreed_amount,
                c.status,
                g.budget,
                e.escrow_id,
                e.funded_at,
                e.released_at,
                u.created_at AS freelancer_created_at
            FROM Contracts c
            JOIN Gigs g ON g.gig_id = c.gig_id
            JOIN Escrows e ON e.contract_id = c.contract_id
            JOIN Users u ON u.user_id = c.freelancer_id
            WHERE c.contract_id = ?
            """,
            (contract_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Contract not found.")

        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    finally:
        cursor.close()
        conn.close()


def score_contract(contract_id: int) -> dict:
    """Runs a set of explainable, threshold-based rules against a contract
    and its associated gig/bid/escrow data. Each triggered rule contributes
    a fixed number of points and a plain-language reason, so the final score
    can always be traced back to exactly which conditions caused it —
    no black-box model involved."""

    context = _get_contract_context(contract_id)

    score = 0
    reasons = []

    budget = float(context["budget"])
    agreed_amount = float(context["agreed_amount"])
    bid_ratio = agreed_amount / budget if budget > 0 else 1.0

    # Rule 1: Lowball bid
    if bid_ratio < LOWBALL_BID_RATIO:
        score += 30
        reasons.append(
            f"Agreed amount (₹{agreed_amount:,.2f}) is only "
            f"{bid_ratio * 100:.0f}% of the gig's budget (₹{budget:,.2f}), "
            f"well below the {LOWBALL_BID_RATIO * 100:.0f}% threshold. "
            f"Unusually low bids can be used to win a contract with no "
            f"intention of delivering full-scope work."
        )

    # Rule 2: Overbid
    if bid_ratio > OVERBID_RATIO:
        score += 15
        reasons.append(
            f"Agreed amount (₹{agreed_amount:,.2f}) is {bid_ratio * 100:.0f}% "
            f"of the gig's stated budget (₹{budget:,.2f}), exceeding the "
            f"{OVERBID_RATIO * 100:.0f}% threshold."
        )

    # Rule 3: Fast fund-to-release (escrow round-tripped too quickly)
    funded_at = context["funded_at"]
    released_at = context["released_at"]
    if funded_at and released_at:
        elapsed_seconds = (released_at - funded_at).total_seconds()
        if 0 <= elapsed_seconds < FAST_RELEASE_SECONDS:
            score += 25
            reasons.append(
                f"Escrow was funded and released only {elapsed_seconds:.0f} "
                f"seconds apart, under the {FAST_RELEASE_SECONDS}-second "
                f"threshold. Genuine work is rarely completed and approved "
                f"this quickly for a contract of this value."
            )

    # Rule 4: Very new freelancer account taking on this contract
    freelancer_created_at = context["freelancer_created_at"]
    if freelancer_created_at:
        account_age_hours = (
            datetime.now(timezone.utc).replace(tzinfo=None) - freelancer_created_at
        ).total_seconds() / 3600
        if account_age_hours < NEW_ACCOUNT_HOURS:
            score += 20
            reasons.append(
                f"Freelancer account is only {account_age_hours:.1f} hours "
                f"old, under the {NEW_ACCOUNT_HOURS}-hour threshold. New "
                f"accounts taking on funded contracts carry higher risk."
            )

    # Rule 5: Large transaction, flagged for review regardless of other signals
    if agreed_amount >= LARGE_TRANSACTION_AMOUNT:
        score += 10
        reasons.append(
            f"Contract value (₹{agreed_amount:,.2f}) meets or exceeds the "
            f"₹{LARGE_TRANSACTION_AMOUNT:,.2f} large-transaction review "
            f"threshold."
        )

    if not reasons:
        reasons.append("No fraud indicators were triggered by the current rule set.")

    tier = _tier_for_score(score)

    result = {
        "contract_id": contract_id,
        "gig_id": context["gig_id"],
        "client_id": context["client_id"],
        "freelancer_id": context["freelancer_id"],
        "agreed_amount": agreed_amount,
        "budget": budget,
        "risk_score": score,
        "risk_tier": tier,
        "reasons": reasons,
    }

    # Log the scoring decision to MongoDB for audit purposes — the same
    # activity-logging path already used elsewhere in the project.
    try:
        log_activity(
            event_type="FRAUD_SCORE",
            user_id=context["freelancer_id"],
            transaction_id=None,
            amount=agreed_amount,
            details=result,
        )
    except Exception:
        # Fraud scoring should not fail just because logging failed.
        pass

    return result
