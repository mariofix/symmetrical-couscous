"""Database connection utilities for PyDBA.

Connections are never stored persistently – they are created on-demand from
the (HMAC-signed) session data supplied by the logged-in user.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import MetaData, Table, create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------------------

DRIVER_MAP: dict[str, str] = {
    "mysql": "mysql+pymysql",
    "postgresql": "postgresql+psycopg2",
    "sqlite": "sqlite",
}


def build_url(conn_info: dict[str, Any]) -> str:
    """Return a SQLAlchemy URL from the *conn_info* session dictionary."""
    db_type = conn_info.get("db_type", "mysql")
    driver = DRIVER_MAP.get(db_type, "mysql+pymysql")

    if db_type == "sqlite":
        db_path = conn_info.get("database", ":memory:")
        return f"sqlite:///{db_path}"

    user = quote_plus(conn_info.get("username", ""))
    password = quote_plus(conn_info.get("password", ""))
    host = conn_info.get("host", "localhost")
    port = conn_info.get("port", _default_port(db_type))
    database = conn_info.get("database", "")

    auth = f"{user}:{password}@" if user else ""
    db_part = f"/{database}" if database else ""
    return f"{driver}://{auth}{host}:{port}{db_part}"


def _default_port(db_type: str) -> int:
    return {"mysql": 3306, "postgresql": 5432}.get(db_type, 3306)


# ---------------------------------------------------------------------------
# Identifier validation
# ---------------------------------------------------------------------------

# Allow only names that contain word characters, dollar signs, and hyphens.
# This covers all real-world table/database names while blocking injection.
_IDENT_RE = re.compile(r"^[\w$][\w$\-]*$", re.UNICODE)


def _validate_identifier(name: str) -> str:
    """Return *name* unchanged if it is a safe SQL identifier, else raise.

    This prevents SQL injection through table/database names that arrive as
    URL path parameters.
    """
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

def make_engine(conn_info: dict[str, Any], database: str | None = None) -> Engine:
    """Create a SQLAlchemy :class:`Engine` from *conn_info*.

    If *database* is given it overrides whatever is in *conn_info*.
    """
    info = dict(conn_info)
    if database is not None:
        info["database"] = database
    url = build_url(info)
    return create_engine(url, pool_pre_ping=True, future=True)


# ---------------------------------------------------------------------------
# High-level helpers used by routes
# ---------------------------------------------------------------------------

def list_databases(engine: Engine) -> list[str]:
    """Return all database names visible from *engine*'s connection."""
    dialect = engine.dialect.name
    with engine.connect() as conn:
        if dialect == "mysql":
            rows = conn.execute(text("SHOW DATABASES")).fetchall()
            return [r[0] for r in rows]
        if dialect == "postgresql":
            rows = conn.execute(
                text("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
            ).fetchall()
            return [r[0] for r in rows]
        if dialect == "sqlite":
            return ["main"]
    return []


def list_tables(engine: Engine) -> list[str]:
    """Return all table (and view) names in the current database."""
    insp = inspect(engine)
    tables = insp.get_table_names()
    views = insp.get_view_names()
    return sorted(tables + views)


def table_row_count(engine: Engine, table: str) -> int:
    """Return an approximate row count for *table*."""
    _validate_identifier(table)
    dialect = engine.dialect.name
    with engine.connect() as conn:
        if dialect == "mysql":
            row = conn.execute(
                text(
                    "SELECT TABLE_ROWS FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
                ),
                {"t": table},
            ).fetchone()
            if row and row[0] is not None:
                return int(row[0])
        # Fallback – exact count via SQLAlchemy reflection (no identifier interpolation)
        meta = MetaData()
        tbl = Table(table, meta, autoload_with=engine)
        row = conn.execute(select(func.count()).select_from(tbl)).fetchone()
        return int(row[0]) if row else 0


def get_table_structure(engine: Engine, table: str) -> list[dict[str, Any]]:
    """Return column metadata for *table*."""
    insp = inspect(engine)
    columns = insp.get_columns(table)
    pk_constraint = insp.get_pk_constraint(table)
    pk_cols = set(pk_constraint.get("constrained_columns", []))
    result = []
    for col in columns:
        result.append(
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": col.get("default"),
                "primary_key": col["name"] in pk_cols,
            }
        )
    return result


def get_table_indexes(engine: Engine, table: str) -> list[dict[str, Any]]:
    """Return index metadata for *table*."""
    insp = inspect(engine)
    return insp.get_indexes(table)


def browse_table(
    engine: Engine,
    table: str,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Return (columns, rows) for a paginated browse of *table*.

    Uses SQLAlchemy's Table reflection so identifiers are always properly
    quoted by the dialect – no raw string interpolation.
    """
    _validate_identifier(table)
    offset = (page - 1) * page_size
    meta = MetaData()
    tbl = Table(table, meta, autoload_with=engine)
    stmt = select(tbl).limit(page_size).offset(offset)
    with engine.connect() as conn:
        result = conn.execute(stmt)
        columns = list(result.keys())
        rows = [tuple(r) for r in result.fetchall()]
    return columns, rows


def execute_query(
    engine: Engine, sql: str, max_rows: int = 1000
) -> dict[str, Any]:
    """Execute *sql* and return a result dict with columns, rows, rowcount, error."""
    try:
        with engine.begin() as conn:
            result = conn.execute(text(sql))
            if result.returns_rows:
                columns = list(result.keys())
                rows = [tuple(r) for r in result.fetchmany(max_rows)]
                return {
                    "columns": columns,
                    "rows": rows,
                    "rowcount": len(rows),
                    "error": None,
                    "truncated": len(rows) == max_rows,
                }
            return {
                "columns": [],
                "rows": [],
                "rowcount": result.rowcount,
                "error": None,
                "truncated": False,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "columns": [],
            "rows": [],
            "rowcount": 0,
            "error": str(exc),
            "truncated": False,
        }
