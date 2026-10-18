# DUX Vault Backend

FastAPI backend scaffold for legacy document retrieval.

## Setup

1. Copy `.env.example` to `.env.development`.
2. Fill required values, including the Active Directory settings (`LDAP_SERVERS`, `LDAP_BASE_DN`, `LDAP_DOMAIN_NETBIOS`, `LDAP_CA_CERT_FILE`, `LDAP_GROUP_GENERAL`, `LDAP_GROUP_CONFIDENTIAL`) and `FRONTEND_ORIGINS`. Note the entitlement groups and the service account are named with a leading `#` - `#IDM-GENERAL`, `#IDM-CONFIDENTIAL`, `CORP\#IDM-SRVC` - and omitting it silently matches nothing.
3. If your SQL Server uses a self-signed certificate in local development, keep `DB_TRUST_SERVER_CERTIFICATE=true`.
4. Create and activate a virtual environment.
5. Install dependencies: `pip install -r requirements.txt`.
6. Generate the CA bundle `LDAP_CA_CERT_FILE` points at: `PYTHONPATH=. python scripts/fetch_ca_cert.py --user 'CORP\yourname'`. Sign-in fails closed without it, and this needs a real terminal because it prompts for a password.
7. Run API: `make dev`, or `make serve` to serve the built frontend over https as well.

## Commands

- `make install` - install dependencies from `requirements.txt`.
- `make dev` - run FastAPI with autoreload (API only, plain http).
- `make build-frontend` - build the SPA into `static/`.
- `make tls-cert` - generate a self-signed TLS certificate.
- `make serve` - serve the API and the SPA over https on all interfaces.
- `make url` - print the URL to hand out.
- `make test` - run pytest.
- `make lint` - run ruff checks.
- `make format` - run ruff formatter.
- `make check` - run compile, lint, and tests.

## Diagnosing Sign-in

`scripts/check_ad_login.py` reports what the application would actually see for one account:
whether the bind succeeds, whether group membership can be read, whether the configured
entitlement groups exist under the name the app compares, and the entitlements that result. It
distinguishes the causes that otherwise all surface as an identical 403.

```bash
PYTHONPATH=. python scripts/check_ad_login.py --user 'CORP\yourname'

# Bind as one account and read another's membership - the only way to test whether the
# LDAP_BIND_DN service account can act as the group-read fallback.
PYTHONPATH=. python scripts/check_ad_login.py --user 'CORP\#IDM-SRVC' --for yourname
```

Reading a failure: **500** means the CA bundle or directory config is wrong, **503** that no
domain controller was reachable, **401** that the password was rejected, and **403** that the
password was *accepted* but the account holds neither entitlement group.

## Local Dev Auth Bypass

`AUTH_BYPASS_ENABLED=true` lets you exercise the DB queries and document routes when the
directory is unreachable.

**It is not a login shortcut.** With it on, `get_current_user` returns a fully-entitled
stand-in user **with no session cookie at all**, and the entitlement check returns early - so
every endpoint is open to anyone who can reach the host, Confidential documents included. With
`AUTH_BYPASS_GROUPS` empty the stand-in holds both entitlements.

- Set `AUTH_BYPASS_ENABLED=true` in `.env.development`.
- Optionally set `AUTH_BYPASS_USERNAME`, `AUTH_BYPASS_DISPLAY_NAME`, `AUTH_BYPASS_EMAIL`, and `AUTH_BYPASS_GROUPS`.
- Restart the API - `--reload` watches `.py` files, not `.env`.

Never enable it on a host anyone else can reach. `Settings.validate_for_runtime` refuses to
start with it on when `APP_ENV` is production, and warns in the log otherwise.

## Logging

- Development uses readable console logs.
- Production uses JSON logs so log collectors can parse fields consistently.

## Structure

- `app/api/routes` - thin HTTP routes.
- `app/auth` - Active Directory sign-in, login throttling, and auth dependencies.
- `app/db` - SQLAlchemy engines, models, and query modules.
- `app/services` - path resolving and file streaming logic.
- `app/schemas` - pydantic response models.
- `scripts` - indexing job, plus the Active Directory diagnostics described above.
- `certs` - generated: the corporate CA bundle and the self-signed TLS pair. Gitignored.
- `static` - generated: the built SPA, served by `app.main`. Gitignored.
