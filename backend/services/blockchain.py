import hashlib
import json
from datetime import datetime, timezone

from backend.database import get_db_connection


def calculate_hash(block_data: dict) -> str:
    block_string = json.dumps(
        block_data,
        sort_keys=True,
        default=str
    ).encode()

    return hashlib.sha256(block_string).hexdigest()


def add_transaction_to_ledger(transaction_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Get transaction data
        cursor.execute("""
            SELECT
                transaction_id,
                escrow_id,
                sender_id,
                receiver_id,
                amount,
                transaction_type
            FROM Transactions
            WHERE transaction_id = ?
        """, transaction_id)

        transaction = cursor.fetchone()

        if not transaction:
            raise ValueError("Transaction not found.")

        # Get previous block hash
        cursor.execute("""
            SELECT TOP 1 current_hash
            FROM LedgerBlocks
            ORDER BY block_id DESC
        """)

        previous_block = cursor.fetchone()

        previous_hash = (
            previous_block[0]
            if previous_block
            else "GENESIS"
        )

        timestamp = datetime.now(timezone.utc).isoformat()

        block_data = {
            "transaction_id": transaction.transaction_id,
            "escrow_id": transaction.escrow_id,
            "sender_id": transaction.sender_id,
            "receiver_id": transaction.receiver_id,
            "amount": float(transaction.amount),
            "transaction_type": transaction.transaction_type,
            "timestamp": timestamp,
            "previous_hash": previous_hash
        }

        current_hash = calculate_hash(block_data)

        cursor.execute("""
           INSERT INTO LedgerBlocks (
                transaction_id,
                escrow_id,
                sender_id,
                receiver_id,
                amount,
                transaction_type,
                previous_hash,
                current_hash,
                hash_timestamp
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
        transaction.transaction_id,
        transaction.escrow_id,
        transaction.sender_id,
        transaction.receiver_id,
        transaction.amount,
        transaction.transaction_type,
        previous_hash,
        current_hash,
        timestamp)

        connection.commit()

        return {
            "message": "Ledger block created successfully",
            "transaction_id": transaction_id,
            "previous_hash": previous_hash,
            "current_hash": current_hash
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


def verify_ledger():
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT
                block_id,
                transaction_id,
                escrow_id,
                sender_id,
                receiver_id,
                amount,
                transaction_type,
                previous_hash,
                current_hash,
                hash_timestamp
            FROM LedgerBlocks
            ORDER BY block_id ASC
        """)

        blocks = cursor.fetchall()

        if not blocks:
            return {
                "status": "valid",
                "message": "Ledger is empty."
            }

        expected_previous_hash = "GENESIS"

        for block in blocks:
            block_data = {
                "transaction_id": block.transaction_id,
                "escrow_id": block.escrow_id,
                "sender_id": block.sender_id,
                "receiver_id": block.receiver_id,
                "amount": float(block.amount),
                "transaction_type": block.transaction_type,
                "timestamp": block.hash_timestamp,
                "previous_hash": block.previous_hash
            }

            recalculated_hash = calculate_hash(block_data)

            if block.previous_hash != expected_previous_hash:
                return {
                    "status": "invalid",
                    "message": "Broken chain detected",
                    "block_id": block.block_id
                }

            if block.current_hash != recalculated_hash:
                return {
                    "status": "invalid",
                    "message": "Tampering detected",
                    "block_id": block.block_id
                }

            expected_previous_hash = block.current_hash

        return {
            "status": "valid",
            "message": "Ledger integrity verified successfully",
            "blocks_verified": len(blocks)
        }

    finally:
        cursor.close()
        connection.close()