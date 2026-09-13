from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from mongo.auth_users import decode_token

security_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    """FastAPI dependency: requires 'Authorization: Bearer <token>' header.
    Raises 401 if missing/invalid/expired. Returns the decoded token payload
    (sub=user_id, email, role, exp, iat) on success."""
    token = credentials.credentials

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    return payload