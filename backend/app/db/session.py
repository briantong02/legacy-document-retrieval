from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings


def _connection_string(database: str) -> str:
    settings = get_settings()
    driver = "ODBC Driver 18 for SQL Server"
    trust_server_certificate = "yes" if settings.db_trust_server_certificate else "no"

    return (
        f"mssql+pyodbc://{quote_plus(settings.db_user)}:{quote_plus(settings.db_password)}"
        f"@{settings.db_server}/{database}?driver={driver.replace(' ', '+')}"
        f"&Encrypt=yes&TrustServerCertificate={trust_server_certificate}"
    )


def create_idm_engine() -> Engine:
    return create_engine(_connection_string("Infor_duxprod_DocMgmt"), pool_pre_ping=True)


def create_docmgmt_engine() -> Engine:
    return create_engine(_connection_string("DUX_DocMgmt"), pool_pre_ping=True)


idm_engine = create_idm_engine()
docmgmt_engine = create_docmgmt_engine()
