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
    attributes: dict[str, str] | None = None


class SessionManager:
    def __init__(self, session_ttl_seconds: int = 28800) -> None:
        self.session_ttl_seconds = session_ttl_seconds
        self.sessions: dict[str, tuple[AuthenticatedUser, float]] = {}

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


class LocalAuthProvider:
    name = "local"

    def __init__(self, users: dict[str, dict]) -> None:
        self.users = users

    @classmethod
    def from_environment(cls) -> "LocalAuthProvider":
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

        return AuthenticatedUser(username=username, role=record.get("role", "readonly"), attributes={})


class LdapAuthProvider:
    name = "ldap"

    def __init__(
        self,
        uri: str,
        base_dn: str,
        bind_dn: str,
        bind_password: str,
        user_filter: str,
        default_role: str,
        group_role_map: dict[str, str],
    ) -> None:
        if not uri or not base_dn or not user_filter:
            raise ValueError("LDAP requires NETBROKER_LDAP_URI, NETBROKER_LDAP_BASE_DN, and NETBROKER_LDAP_USER_FILTER")
        try:
            import ldap
        except ImportError as exc:
            raise RuntimeError("Install python3-ldap to use LDAP authentication") from exc

        self.ldap = ldap
        self.uri = uri
        self.base_dn = base_dn
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.user_filter = user_filter
        self.default_role = default_role
        self.group_role_map = group_role_map

    @classmethod
    def from_environment(cls) -> "LdapAuthProvider":
        return cls(
            uri=os.environ.get("NETBROKER_LDAP_URI", ""),
            base_dn=os.environ.get("NETBROKER_LDAP_BASE_DN", ""),
            bind_dn=os.environ.get("NETBROKER_LDAP_BIND_DN", ""),
            bind_password=os.environ.get("NETBROKER_LDAP_BIND_PASSWORD", ""),
            user_filter=os.environ.get("NETBROKER_LDAP_USER_FILTER", "(sAMAccountName={username})"),
            default_role=os.environ.get("NETBROKER_LDAP_DEFAULT_ROLE", "readonly"),
            group_role_map=parse_group_role_map(os.environ.get("NETBROKER_LDAP_GROUP_ROLE_MAP", "")),
        )

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        if not username or not password:
            return None

        connection = self._connect()
        try:
            if self.bind_dn:
                connection.simple_bind_s(self.bind_dn, self.bind_password)
            else:
                connection.simple_bind_s()

            safe_username = username.replace("\\", "\\5c").replace("*", "\\2a").replace("(", "\\28").replace(")", "\\29")
            search_filter = self.user_filter.format(username=safe_username)
            attrs = ["dn", "memberOf", "cn", "sAMAccountName", "uid"]
            result = connection.search_s(self.base_dn, self.ldap.SCOPE_SUBTREE, search_filter, attrs)
            if not result:
                return None

            user_dn, user_attrs = result[0]
        finally:
            connection.unbind_s()

        user_connection = self._connect()
        try:
            user_connection.simple_bind_s(user_dn, password)
        except self.ldap.INVALID_CREDENTIALS:
            return None
        finally:
            user_connection.unbind_s()

        role = self.role_for(user_attrs)
        return AuthenticatedUser(username=username, role=role, attributes={"groups": ";".join(groups)})

    def role_for(self, attrs: dict) -> str:
        groups = [value.decode("utf-8") if isinstance(value, bytes) else str(value) for value in attrs.get("memberOf", [])]
        for group_dn, role in self.group_role_map.items():
            if group_dn in groups:
                return role
        return self.default_role

    def _connect(self):
        connection = self.ldap.initialize(self.uri)
        connection.set_option(self.ldap.OPT_REFERRALS, 0)
        return connection


class TacacsAuthProvider:
    name = "tacacs"

    def __init__(
        self,
        host: str,
        secret: str,
        port: int,
        timeout: int,
        default_role: str,
        user_role_map: dict[str, str],
    ) -> None:
        if not host or not secret:
            raise ValueError("TACACS+ requires NETBROKER_TACACS_HOST and NETBROKER_TACACS_SECRET")
        try:
            from tacacs_plus.client import TACACSClient
            from tacacs_plus.flags import TAC_PLUS_AUTHEN_TYPE_ASCII
        except ImportError as exc:
            raise RuntimeError("Install tacacs_plus to use TACACS+ authentication") from exc

        self.client_class = TACACSClient
        self.auth_type = TAC_PLUS_AUTHEN_TYPE_ASCII
        self.host = host
        self.secret = secret
        self.port = port
        self.timeout = timeout
        self.default_role = default_role
        self.user_role_map = user_role_map

    @classmethod
    def from_environment(cls) -> "TacacsAuthProvider":
        return cls(
            host=os.environ.get("NETBROKER_TACACS_HOST", ""),
            secret=os.environ.get("NETBROKER_TACACS_SECRET", ""),
            port=int(os.environ.get("NETBROKER_TACACS_PORT", "49")),
            timeout=int(os.environ.get("NETBROKER_TACACS_TIMEOUT", "5")),
            default_role=os.environ.get("NETBROKER_TACACS_DEFAULT_ROLE", "readonly"),
            user_role_map=parse_user_role_map(os.environ.get("NETBROKER_TACACS_USER_ROLE_MAP", "")),
        )

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        if not username or not password:
            return None

        client = self.client_class(
            self.host,
            self.port,
            self.secret,
            timeout=self.timeout,
        )
        response = client.authenticate(username, password, authen_type=self.auth_type)
        if not getattr(response, "valid", False):
            return None

        role = self.user_role_map.get(username, self.default_role)
        return AuthenticatedUser(username=username, role=role, attributes={})


class IseAuthorizationPolicy:
    name = "ise"

    def __init__(
        self,
        enabled: bool,
        default_role: str,
        user_role_map: dict[str, str],
        profile_role_map: dict[str, str],
        sgt_role_map: dict[str, str],
    ) -> None:
        self.enabled = enabled
        self.default_role = default_role
        self.user_role_map = user_role_map
        self.profile_role_map = profile_role_map
        self.sgt_role_map = sgt_role_map

    @classmethod
    def from_environment(cls) -> "IseAuthorizationPolicy":
        return cls(
            enabled=os.environ.get("NETBROKER_ISE_ENABLED", "false").lower() in {"1", "true", "yes", "on"},
            default_role=os.environ.get("NETBROKER_ISE_DEFAULT_ROLE", ""),
            user_role_map=parse_user_role_map(os.environ.get("NETBROKER_ISE_USER_ROLE_MAP", "")),
            profile_role_map=parse_user_role_map(os.environ.get("NETBROKER_ISE_PROFILE_ROLE_MAP", "")),
            sgt_role_map=parse_user_role_map(os.environ.get("NETBROKER_ISE_SGT_ROLE_MAP", "")),
        )

    def authorize(self, user: AuthenticatedUser) -> AuthenticatedUser:
        if not self.enabled:
            return user

        attributes = dict(user.attributes or {})
        role = user.role

        ise_profile = attributes.get("ise_profile") or attributes.get("profile") or ""
        ise_sgt = attributes.get("ise_sgt") or attributes.get("sgt") or ""

        if user.username in self.user_role_map:
            role = self.user_role_map[user.username]
        elif ise_profile in self.profile_role_map:
            role = self.profile_role_map[ise_profile]
        elif ise_sgt in self.sgt_role_map:
            role = self.sgt_role_map[ise_sgt]
        elif self.default_role:
            role = self.default_role

        attributes["ise_authorized"] = "true"
        return AuthenticatedUser(username=user.username, role=role, attributes=attributes)


class AuthService:
    def __init__(self, provider, sessions: SessionManager | None = None, authorization_policy: IseAuthorizationPolicy | None = None) -> None:
        self.provider = provider
        self.sessions = sessions or SessionManager()
        self.authorization_policy = authorization_policy or IseAuthorizationPolicy.from_environment()

    @classmethod
    def from_environment(cls) -> "AuthService":
        provider_name = os.environ.get("NETBROKER_AUTH_PROVIDER", "local")
        if provider_name == "ldap":
            provider = LdapAuthProvider.from_environment()
        elif provider_name == "tacacs":
            provider = TacacsAuthProvider.from_environment()
        else:
            provider = LocalAuthProvider.from_environment()
        return cls(provider, authorization_policy=IseAuthorizationPolicy.from_environment())

    @property
    def provider_name(self) -> str:
        if self.authorization_policy.enabled:
            return f"{self.provider.name}+ise"
        return self.provider.name

    def authenticate(self, username: str, password: str) -> AuthenticatedUser | None:
        user = self.provider.authenticate(username, password)
        if not user:
            return None
        return self.authorization_policy.authorize(user)

    def create_session(self, user: AuthenticatedUser) -> str:
        return self.sessions.create_session(user)

    def resolve_session(self, token: str | None) -> AuthenticatedUser | None:
        return self.sessions.resolve_session(token)

    def destroy_session(self, token: str | None) -> None:
        self.sessions.destroy_session(token)

    def can(self, user: AuthenticatedUser, minimum_role: str) -> bool:
        return self.sessions.can(user, minimum_role)


def parse_group_role_map(raw: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in raw.split(";"):
        group_dn, separator, role = item.rpartition("=")
        if separator and group_dn.strip() and role.strip():
            mapping[group_dn.strip()] = role.strip()
    return mapping


def parse_user_role_map(raw: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in raw.split(";"):
        username, separator, role = item.partition("=")
        if separator and username.strip() and role.strip():
            mapping[username.strip()] = role.strip()
    return mapping


def _hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return base64.b64encode(digest).decode("ascii")
