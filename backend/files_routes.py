import base64
import binascii
import hashlib
import os
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from backend.auth_dependency import get_current_user
from backend.database import get_db_connection

router = APIRouter(tags=["deliverables"])

MAX_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".zip", ".txt", ".md",
                      ".csv", ".docx", ".pptx", ".xlsx"}


class UploadRequest(BaseModel):
    file_name: str
    content_type: str = "application/octet-stream"
    data_base64: str
    note: str = ""


def _contract_parties(cursor, contract_id):
    cursor.execute(
        "SELECT client_id, freelancer_id, status FROM Contracts WHERE contract_id = ?",
        (contract_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Contract not found.")
    return int(row[0]), int(row[1]), str(row[2])


def _check_access(user, client_id, freelancer_id):
    uid = int(user["sub"])
    role = str(user.get("role", "")).upper()
    if role != "ADMIN" and uid not in (client_id, freelancer_id):
        raise HTTPException(status_code=403, detail="You are not a party to this contract.")


@router.post("/contracts/{contract_id}/deliverable")
def upload_deliverable(contract_id: int, req: UploadRequest, user=Depends(get_current_user)):
    name = os.path.basename(req.file_name.strip())
    ext = os.path.splitext(name)[1].lower()
    if not name or ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400,
                            detail="File type not allowed. Allowed: " + ", ".join(sorted(ALLOWED_EXTENSIONS)))
    try:
        data = base64.b64decode(req.data_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="The file data is not valid.")
    if len(data) == 0 or len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File must be between 1 byte and 5 MB.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        client_id, freelancer_id, status = _contract_parties(cursor, contract_id)
        if int(user["sub"]) != freelancer_id:
            raise HTTPException(status_code=403, detail="Only the freelancer on this contract can upload work.")
        if status != "ACTIVE":
            raise HTTPException(status_code=400, detail="Work can only be uploaded while the contract is active.")
        digest = hashlib.sha256(data).hexdigest()
        cursor.execute(
            "INSERT INTO ContractFiles (contract_id, file_name, content_type, size_bytes, sha256, note, file_data, uploaded_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (contract_id, name, req.content_type[:100], len(data), digest, req.note[:500], data, int(user["sub"])),
        )
        conn.commit()
        return {"status": "uploaded", "file_name": name, "size_bytes": len(data), "sha256": digest}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/contracts/{contract_id}/deliverable/info")
def deliverable_info(contract_id: int, user=Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        client_id, freelancer_id, _ = _contract_parties(cursor, contract_id)
        _check_access(user, client_id, freelancer_id)
        cursor.execute(
            "SELECT TOP 1 file_name, content_type, size_bytes, sha256, note, uploaded_at "
            "FROM ContractFiles WHERE contract_id = ? ORDER BY file_id DESC",
            (contract_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {"has_file": False}
        return {"has_file": True, "file_name": row[0], "content_type": row[1],
                "size_bytes": row[2], "sha256": row[3], "note": row[4],
                "uploaded_at": row[5].isoformat()}
    finally:
        cursor.close()
        conn.close()


@router.get("/contracts/{contract_id}/deliverable")
def download_deliverable(contract_id: int, user=Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        client_id, freelancer_id, _ = _contract_parties(cursor, contract_id)
        _check_access(user, client_id, freelancer_id)
        cursor.execute(
            "SELECT TOP 1 file_name, content_type, file_data, sha256 "
            "FROM ContractFiles WHERE contract_id = ? ORDER BY file_id DESC",
            (contract_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No work has been uploaded yet.")
        data = bytes(row[2])
        return Response(
            content=data,
            media_type=row[1],
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''" + quote(row[0]),
                "X-Content-SHA256": row[3],
            },
        )
    finally:
        cursor.close()
        conn.close()
