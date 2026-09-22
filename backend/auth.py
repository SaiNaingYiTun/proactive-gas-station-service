"""Password hashing and login tokens for the staff dashboard.

Only the DASHBOARD is gated by this -- the AI module's own machine-to-machine
endpoints (POST /api/detection, PUT /api/exit, PATCH /api/entry/{id}) are
unrelated to a staff member logging in and are left exactly as they were.

Token design: a signed JWT carries the account's id, username, is_owner flag,
and the account row's updated_at *at the moment the token was issued*. Every
authenticated request re-reads the CURRENT row and compares that stamp --
not just the JWT signature -- because a plain stateless JWT would stay valid
until its natural expiry even after the owner changes that account's
username/password (exactly the "fired employee" case this exists for). A
credential change always bumps updated_at, so the old token is rejected on
its very next use, not just eventually.
"""

import os
import time
from datetime import datetime, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Header, HTTPException
from fastapi.security.utils import get_authorization_scheme_param

JWT_ALGORITHM = "HS256"
# A work shift is a handful of hours; long enough that nobody has to log
# back in mid-shift, short enough that a token left on a shared computer
# doesn't stay usable for days.
TOKEN_TTL_HOURS = 12


def _jwt_secret():
    secret = os.getenv("JWT_SECRET")
    if not secret:
        # Fail loudly rather than silently signing tokens with a guessable
        # default -- an auth system nobody can forge tokens for is the
        # entire point of adding one.
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
        # A malformed/empty hash must fail closed, not raise past the caller.
        return False


def _row_updated_at_epoch(row: dict) -> float:
    """vehicle_visits/staff_accounts timestamps come back from Supabase as
    ISO-8601 strings; normalise to a float so it can be embedded in a JWT
    (whose claims must be JSON-serialisable) and compared cheaply."""
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
    """Verify signature and expiry only -- the caller still must compare
    ``upd`` against the account's current row; this function has no DB
    access and cannot do that part itself."""
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
    """FastAPI dependency: verifies the bearer token AND that the account it
    names still has the same credentials as when the token was issued.

    Takes the Supabase client via a setter rather than importing it, since
    main.py (which creates that client) already imports this module --
    importing it back would be circular.
    """

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
            # This account's username/password changed since this token was
            # issued -- the exact case updated_at exists to catch.
            raise HTTPException(status_code=401, detail="Session expired or invalid, please log in again")
        if self.require_owner and not account["is_owner"]:
            raise HTTPException(status_code=403, detail="Only the owner can do this")
        return account
