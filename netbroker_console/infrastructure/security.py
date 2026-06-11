from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass


ROLE_LEVELS = {
    "readonly": 1,
    "auditor": 2,
    "noc": 3,
    "admin": 4,
}


@dataclass(frozen=True)
class AuthenticatedUser:
    username: str
    role: str


class LocalAuthService:
    def __init__(self, users: dict[str, dict], session_ttl_seconds: int = 28800) -> None:
        self.users = users
        self.session_ttl_seconds = session_ttl_seconds
        self.sessions: dict[str, tuple[AuthenticatedUser, float]] = {}

    @classmethod
    def from_environment(cls) -> "LocalAuthService":
        username = os.environ.get("NETBROKER_ADMIN_USER", "admin")
        password = os.environ.get("NETBROKER_ADMIN_PASSWORD", "admin123")
        role = os.environ.get("NETBROKER_ADMIN_ROLE", "admin")
        salt = secrets.token_bytes(16)
        return cls(
            {
                username: {
                    "role": role,
                    "salt": base64.b64encode(salt).decode("ascii"),
                    "password_hash": _hash_password(password, salt),
                }
            }
        )

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        record = self.users.get(username)
        if not record:
            return None

        salt = base64.b64decode(record["salt"])
        expected = record["password_hash"]
        provided = _hash_password(password, salt)
        if not hmac.compare_digest(expected, provided):
            return None

        return AuthenticatedUser(username=username, role=record.get("role", "readonly"))

    def create_session(self, user: AuthenticatedUser) -> str:
        token = secrets.token_urlsafe(32)
        self.sessions[token] = (user, time.time() + self.session_ttl_seconds)
        return token

    def resolve_session(self, token: str | None) -> AuthenticatedUser | None:
        if not token:
            return None
        session = self.sessions.get(token)
        if not session:
            return None

        user, expires_at = session
        if expires_at < time.time():
            self.sessions.pop(token, None)
            return None
        return user

    def destroy_session(self, token: str | None) -> None:
        if token:
            self.sessions.pop(token, None)

    def can(self, user: AuthenticatedUser, minimum_role: str) -> bool:
        return ROLE_LEVELS.get(user.role, 0) >= ROLE_LEVELS.get(minimum_role, 0)


def _hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return base64.b64encode(digest).decode("ascii")

