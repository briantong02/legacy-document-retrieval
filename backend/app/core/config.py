from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The placeholder shipped in .env.example. It signs session cookies, so booting with it
# still in place would let anyone who knows this string mint a session for any user with
# any entitlements. validate_for_runtime refuses to serve with it in production.
DEFAULT_SESSION_SECRET = "change-this-in-env"


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "DUX Vault Backend"
    api_prefix: str = "/api"
    log_level: str = "INFO"

    db_server: str = ""
    db_user: str = ""
    db_password: str = ""
    db_trust_server_certificate: bool = True

    doc_root_canonical: str = r"e:\DATA1\IT\IDMFiles\infor\infor"
    doc_root_local: str = ""

    # Active Directory / LDAP
    ldap_servers: str = ""
    ldap_port: int = 636
    ldap_use_ssl: bool = True
    ldap_ca_cert_file: str = ""
    ldap_base_dn: str = ""
    ldap_domain_netbios: str = ""
    ldap_domain_dns: str = ""
    ldap_group_general: str = ""
    ldap_group_confidential: str = ""
    ldap_bind_dn: str = ""
    ldap_bind_password: str = ""
    ldap_timeout_seconds: int = 10

    login_max_attempts: int = 5
    login_attempt_window_seconds: int = 300

    frontend_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
    )

    session_secret: str = DEFAULT_SESSION_SECRET
    session_cookie_name: str = "duxvault_session"
    session_cookie_secure: bool = False
    session_cookie_samesite: str = "lax"
    session_max_age_seconds: int = 43200

    auth_bypass_enabled: bool = False
    auth_bypass_username: str = "local.dev"
    auth_bypass_display_name: str = "Local Developer"
    auth_bypass_email: str = "local.dev@duxvault.local"
    auth_bypass_groups: str = ""

    static_dir: str = "static"

    model_config = SettingsConfigDict(
        env_file=".env.development",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def static_path(self) -> Path:
        return Path(self.static_dir)

    @property
    def cors_origins(self) -> list[str]:
        origins = [
            origin.strip().rstrip("/")
            for origin in self.frontend_origins.split(",")
            if origin.strip()
        ]
        return origins or ["http://localhost:5173"]

    @property
    def session_cookie_samesite_value(self) -> str:
        value = self.session_cookie_samesite.strip().lower()
        if value not in {"lax", "strict", "none"}:
            return "lax"
        return value

    @property
    def ldap_servers_list(self) -> list[str]:
        return [server.strip() for server in self.ldap_servers.split(",") if server.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in {"prod", "production"}

    def validate_for_runtime(self) -> list[str]:
        """Refuse to serve on an unsafe configuration; return warnings for the rest.

        `env_file` is hardcoded to .env.development and APP_ENV otherwise only selects the
        log format, so nothing else connects the environment to these settings. Without
        this check, a deployment that forgets one of them starts up and looks healthy while
        being wide open.
        """
        fatal: list[str] = []
        warnings: list[str] = []

        if self.auth_bypass_enabled:
            # Not merely a shortcut past the login form: get_current_user returns a
            # fully-entitled user with no session at all, so every endpoint is open.
            message = (
                "AUTH_BYPASS_ENABLED is on - every request is treated as "
                f"{self.auth_bypass_username!r} with entitlements "
                f"{self.auth_bypass_groups_list}, and no sign-in is required"
            )
            (fatal if self.is_production else warnings).append(message)

        if self.session_secret == DEFAULT_SESSION_SECRET:
            message = "SESSION_SECRET is still the placeholder; session cookies are forgeable"
            (fatal if self.is_production else warnings).append(message)

        if self.is_production and not self.session_cookie_secure:
            fatal.append(
                "SESSION_COOKIE_SECURE is false; the session cookie would travel over plain HTTP"
            )

        if fatal:
            raise RuntimeError(
                "Refusing to start with APP_ENV="
                f"{self.app_env!r}:\n  - " + "\n  - ".join(fatal)
            )

        return warnings

    @property
    def auth_bypass_groups_list(self) -> list[str]:
        groups = [group.strip() for group in self.auth_bypass_groups.split(",") if group.strip()]
        # The bypass user is entitled to everything unless told otherwise.
        return list(dict.fromkeys(groups)) or ["general", "confidential"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
