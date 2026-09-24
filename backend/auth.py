import os
import time
from datetime import datetime, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Header, HTTPException
from fastapi.security.utils import get_authorization_scheme_param

JWT_ALGORITHM = "HS256"

TOKEN_TTL_HOURS = 12


def _jwt_secret():
    secret = os.getenv("JWT_SECRET")
    if not secret:
       
        raise RuntimeError(
            "JWT_SECRET is not set. Add a random value to backend/.env, e.g.:\n"
            '  python -c "import secrets; print(secrets.token_hex(32))"\n'
            "and put the result in JWT_SECRET=... there."
        )
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _row_updated_at_epoch(row: dict) -> float:
    """Convert a Supabase row's updated_at to a float epoch timestamp."""
    value = row["updated_at"]
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def create_token(account: dict) -> str:
    now = int(time.time())
    payload = {
        "sub": str(account["id"]),
        "username": account["username"],
        "is_owner": bool(account["is_owner"]),
        "upd": _row_updated_at_epoch(account),
        "iat": now,
        "exp": now + TOKEN_TTL_HOURS * 3600,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode a JWT token and return its claims, or None if it's invalid."""
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def _bearer_token(authorization: Optional[str]) -> str:
    scheme, token = get_authorization_scheme_param(authorization or "")
    if not authorization or scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


class AuthDependency:
    

    def __init__(self, require_owner: bool = False):
        self.require_owner = require_owner

    def set_client(self, client):
        self._client = client
        return self

    def __call__(self, authorization: Optional[str] = Header(None)):
        token = _bearer_token(authorization)
        claims = decode_token(token)
        if claims is None:
            raise HTTPException(status_code=401, detail="Session expired or invalid, please log in again")

        rows = (
            self._client.table("staff_accounts")
            .select("id, username, display_name, is_owner, active, updated_at")
            .eq("id", claims["sub"])
            .limit(1)
            .execute()
            .data
        )
        if not rows or not rows[0]["active"]:
            raise HTTPException(status_code=401, detail="Session expired or invalid, please log in again")
        account = rows[0]
        if abs(_row_updated_at_epoch(account) - claims["upd"]) > 1e-6:
            raise HTTPException(status_code=401, detail="Session expired or invalid, please log in again")
        if self.require_owner and not account["is_owner"]:
            raise HTTPException(status_code=403, detail="Only the owner can do this")
        return account
