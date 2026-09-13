from fastapi import HTTPException
from backend.database import get_db_connection


def _row_to_dict(cursor, row):
    columns = [column[0] for column in cursor.description]
    return dict(zip(columns, row))


# ---------------------------------------------------------
# GIGS
# ---------------------------------------------------------

def create_gig(client_sql_id: int, title: str, description: str, budget: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO Gigs (client_id, title, description, budget)
            OUTPUT INSERTED.gig_id, INSERTED.status, INSERTED.created_at
            VALUES (?, ?, ?, ?)
            """,
            (client_sql_id, title, description, budget),
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "gig_id": row[0],
            "status": row[1],
            "created_at": str(row[2]),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def list_open_gigs():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT gig_id, client_id, title, description, budget, status, created_at "
            "FROM Gigs WHERE status = 'OPEN' ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        return [_row_to_dict(cursor, row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def get_gig(gig_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT gig_id, client_id, title, description, budget, status, created_at "
            "FROM Gigs WHERE gig_id = ?",
            (gig_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Gig not found.")
        return _row_to_dict(cursor, row)
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# BIDS
# ---------------------------------------------------------

def place_bid(gig_id: int, freelancer_sql_id: int, bid_amount: float, proposal: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT status FROM Gigs WHERE gig_id = ?", (gig_id,))
        gig_row = cursor.fetchone()
        if not gig_row:
            raise HTTPException(status_code=404, detail="Gig not found.")
        if gig_row[0] != "OPEN":
            raise HTTPException(status_code=400, detail="This gig is no longer open for bids.")

        cursor.execute(
            """
            INSERT INTO Bids (gig_id, freelancer_id, bid_amount, proposal)
            OUTPUT INSERTED.bid_id, INSERTED.status, INSERTED.created_at
            VALUES (?, ?, ?, ?)
            """,
            (gig_id, freelancer_sql_id, bid_amount, proposal),
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "bid_id": row[0],
            "status": row[1],
            "created_at": str(row[2]),
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        if "UQ_Bids_Gig_Freelancer" in str(e):
            raise HTTPException(status_code=409, detail="You have already placed a bid on this gig.")
        raise
    finally:
        cursor.close()
        conn.close()


def list_bids_for_gig(gig_id: int, requesting_client_sql_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT client_id FROM Gigs WHERE gig_id = ?", (gig_id,))
        gig_row = cursor.fetchone()
        if not gig_row:
            raise HTTPException(status_code=404, detail="Gig not found.")
        if gig_row[0] != requesting_client_sql_id:
            raise HTTPException(status_code=403, detail="Only the gig's owner can view its bids.")

        cursor.execute(
            "SELECT bid_id, gig_id, freelancer_id, bid_amount, proposal, status, created_at "
            "FROM Bids WHERE gig_id = ? ORDER BY created_at ASC",
            (gig_id,),
        )
        rows = cursor.fetchall()
        return [_row_to_dict(cursor, row) for row in rows]
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# ACCEPTING A BID -> CREATES CONTRACT + ESCROW
# ---------------------------------------------------------

def accept_bid(bid_id: int, requesting_client_sql_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT gig_id, freelancer_id, bid_amount, status FROM Bids WHERE bid_id = ?",
            (bid_id,),
        )
        bid_row = cursor.fetchone()
        if not bid_row:
            raise HTTPException(status_code=404, detail="Bid not found.")

        gig_id, freelancer_id, bid_amount, bid_status = bid_row
        if bid_status != "PENDING":
            raise HTTPException(status_code=400, detail="This bid is no longer pending.")

        cursor.execute("SELECT client_id, status FROM Gigs WHERE gig_id = ?", (gig_id,))
        gig_row = cursor.fetchone()
        gig_client_id, gig_status = gig_row

        if gig_client_id != requesting_client_sql_id:
            raise HTTPException(status_code=403, detail="Only the gig's owner can accept a bid.")
        if gig_status != "OPEN":
            raise HTTPException(status_code=400, detail="This gig is no longer open.")

        cursor.execute("UPDATE Bids SET status = 'ACCEPTED' WHERE bid_id = ?", (bid_id,))
        cursor.execute(
            "UPDATE Bids SET status = 'REJECTED' WHERE gig_id = ? AND bid_id != ?",
            (gig_id, bid_id),
        )
        cursor.execute("UPDATE Gigs SET status = 'IN_PROGRESS' WHERE gig_id = ?", (gig_id,))

        cursor.execute(
            """
            INSERT INTO Contracts (gig_id, client_id, freelancer_id, agreed_amount)
            OUTPUT INSERTED.contract_id
            VALUES (?, ?, ?, ?)
            """,
            (gig_id, requesting_client_sql_id, freelancer_id, bid_amount),
        )
        contract_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO Escrows (contract_id, amount)
            OUTPUT INSERTED.escrow_id
            VALUES (?, ?)
            """,
            (contract_id, bid_amount),
        )
        escrow_id = cursor.fetchone()[0]

        conn.commit()

        return {
            "contract_id": contract_id,
            "escrow_id": escrow_id,
            "gig_id": gig_id,
            "freelancer_id": freelancer_id,
            "agreed_amount": float(bid_amount),
            "status": "ACTIVE",
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# ESCROW FUNDING
# ---------------------------------------------------------

def fund_escrow(contract_id: int, requesting_client_sql_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT client_id, agreed_amount, status FROM Contracts WHERE contract_id = ?",
            (contract_id,),
        )
        contract_row = cursor.fetchone()
        if not contract_row:
            raise HTTPException(status_code=404, detail="Contract not found.")

        client_id, agreed_amount, contract_status = contract_row
        if client_id != requesting_client_sql_id:
            raise HTTPException(status_code=403, detail="Only the contract's client can fund escrow.")
        if contract_status != "ACTIVE":
            raise HTTPException(status_code=400, detail="Contract is not active.")

        cursor.execute("SELECT escrow_id, status FROM Escrows WHERE contract_id = ?", (contract_id,))
        escrow_id, escrow_status = cursor.fetchone()
        if escrow_status != "UNFUNDED":
            raise HTTPException(status_code=400, detail="Escrow has already been funded.")

        cursor.execute("SELECT balance FROM Users WHERE user_id = ?", (client_id,))
        balance = cursor.fetchone()[0]
        if balance < agreed_amount:
            raise HTTPException(status_code=400, detail="Insufficient balance to fund escrow.")

        cursor.execute(
            "UPDATE Users SET balance = balance - ? WHERE user_id = ?",
            (agreed_amount, client_id),
        )
        cursor.execute(
            "UPDATE Escrows SET status = 'HELD', funded_at = SYSUTCDATETIME() WHERE escrow_id = ?",
            (escrow_id,),
        )
        cursor.execute(
            """
            INSERT INTO Transactions (escrow_id, sender_id, receiver_id, amount, transaction_type, status)
            VALUES (?, ?, NULL, ?, 'ESCROW_FUND', 'SUCCESS')
            """,
            (escrow_id, client_id, agreed_amount),
        )

        conn.commit()

        return {
            "contract_id": contract_id,
            "escrow_id": escrow_id,
            "status": "HELD",
            "amount": float(agreed_amount),
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------
# WORK SUBMISSION + APPROVAL (RELEASES ESCROW)
# ---------------------------------------------------------

def submit_work(contract_id: int, requesting_freelancer_sql_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT freelancer_id, status FROM Contracts WHERE contract_id = ?",
            (contract_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Contract not found.")

        freelancer_id, status = row
        if freelancer_id != requesting_freelancer_sql_id:
            raise HTTPException(status_code=403, detail="Only the assigned freelancer can submit work.")
        if status != "ACTIVE":
            raise HTTPException(status_code=400, detail="Contract is not active.")

        cursor.execute(
            "UPDATE Contracts SET status = 'WORK_SUBMITTED' WHERE contract_id = ?",
            (contract_id,),
        )
        conn.commit()
        return {"contract_id": contract_id, "status": "WORK_SUBMITTED"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def approve_and_release(contract_id: int, requesting_client_sql_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT client_id, freelancer_id, gig_id, status FROM Contracts WHERE contract_id = ?",
            (contract_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Contract not found.")

        client_id, freelancer_id, gig_id, status = row
        if client_id != requesting_client_sql_id:
            raise HTTPException(status_code=403, detail="Only the contract's client can approve completion.")
        if status != "WORK_SUBMITTED":
            raise HTTPException(status_code=400, detail="Work has not been submitted yet.")

        cursor.execute("SELECT escrow_id, amount, status FROM Escrows WHERE contract_id = ?", (contract_id,))
        escrow_id, amount, escrow_status = cursor.fetchone()
        if escrow_status != "HELD":
            raise HTTPException(status_code=400, detail="Escrow is not currently held.")

        cursor.execute(
            "UPDATE Escrows SET status = 'RELEASED', released_at = SYSUTCDATETIME() WHERE escrow_id = ?",
            (escrow_id,),
        )
        cursor.execute(
            "UPDATE Users SET balance = balance + ? WHERE user_id = ?",
            (amount, freelancer_id),
        )
        cursor.execute(
            """
            INSERT INTO Transactions (escrow_id, sender_id, receiver_id, amount, transaction_type, status)
            VALUES (?, ?, ?, ?, 'ESCROW_RELEASE', 'SUCCESS')
            """,
            (escrow_id, client_id, freelancer_id, amount),
        )
        cursor.execute("UPDATE Contracts SET status = 'COMPLETED' WHERE contract_id = ?", (contract_id,))
        cursor.execute("UPDATE Gigs SET status = 'COMPLETED' WHERE gig_id = ?", (gig_id,))

        conn.commit()

        return {
            "contract_id": contract_id,
            "escrow_id": escrow_id,
            "status": "COMPLETED",
            "released_amount": float(amount),
            "paid_to_freelancer_id": freelancer_id,
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()