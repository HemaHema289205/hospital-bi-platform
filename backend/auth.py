"""
Demo authentication.

This is a DEMO login, kept deliberately simple: the accounts live in
backend/auth.py (and can be overridden from .env), not in a user table. It is
enough to put a login screen in front of the dashboard, which is what a
hospital BI tool would have, without turning the project into a user-management
system.

The token is a signed, expiring HMAC string, so it cannot simply be typed by
hand - but passwords are compared in plain text, so do NOT use this to protect
anything real.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from backend import config

# ---------------------------------------------------------------- accounts
# Username -> account details. The admin password can be changed in .env.
USERS: dict[str, dict] = {
    "admin": {
        "password": os.getenv("ADMIN_PASSWORD", "admin123"),
        "name": "Hema",
        "role": "Hospital Administrator",
    },
    "doctor": {
        "password": os.getenv("DOCTOR_PASSWORD", "doctor123"),
        "name": "Dr. Ravi Kumar",
        "role": "Doctor",
    },
    "staff": {
        "password": os.getenv("STAFF_PASSWORD", "staff123"),
        "name": "Keerthi",
        "role": "Operations Staff",
    },
}

SECRET = os.getenv("AUTH_SECRET", "hospitalflow-demo-secret-change-me")
TOKEN_HOURS = int(os.getenv("TOKEN_HOURS", "12"))


class AuthError(Exception):
    pass


# ------------------------------------------------------------------ token
def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload: str) -> str:
    return _b64(hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).digest())


def make_token(username: str) -> str:
    body = _b64(json.dumps({
        "sub": username,
        "exp": int(time.time()) + TOKEN_HOURS * 3600,
    }).encode())
    return f"{body}.{_sign(body)}"


def read_token(token: str) -> dict:
    """Returns the account for a valid token, or raises AuthError."""
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        raise AuthError("Malformed token")

    # compare_digest instead of == so the check cannot be timed
    if not hmac.compare_digest(signature, _sign(body)):
        raise AuthError("Invalid token")

    try:
        claims = json.loads(_unb64(body))
    except Exception:                                   # noqa: BLE001
        raise AuthError("Malformed token")

    if claims.get("exp", 0) < time.time():
        raise AuthError("Session expired, please sign in again")

    user = USERS.get(claims.get("sub", ""))
    if not user:
        raise AuthError("Unknown account")

    return public_user(claims["sub"])


# ------------------------------------------------------------------ login
def login(username: str, password: str) -> dict:
    user = USERS.get(username.strip().lower())
    # The same message for both cases, so the form never reveals which
    # usernames exist.
    if not user or not hmac.compare_digest(user["password"], password):
        raise AuthError("Wrong username or password")

    return {
        "token": make_token(username.strip().lower()),
        "expires_in_hours": TOKEN_HOURS,
        "user": public_user(username.strip().lower()),
    }


def public_user(username: str) -> dict:
    """Account details without the password."""
    u = USERS[username]
    return {"username": username, "name": u["name"], "role": u["role"]}


def demo_accounts() -> list[dict]:
    """Shown on the login screen so the demo credentials are never a mystery."""
    return [
        {"username": name, "password": u["password"], "role": u["role"]}
        for name, u in USERS.items()
    ]
