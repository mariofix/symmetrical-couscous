"""Unit tests for the database utility layer (pydba.db)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from pydba.db import (
    _validate_identifier,
    browse_table,
    build_url,
    execute_query,
    get_table_structure,
    list_databases,
    list_tables,
    make_engine,
    table_row_count,
)

# ---------------------------------------------------------------------------
# Identifier validation
# ---------------------------------------------------------------------------


class TestValidateIdentifier:
    def test_valid_simple_name(self):
        assert _validate_identifier("users") == "users"

    def test_valid_name_with_underscore(self):
        assert _validate_identifier("my_table_2") == "my_table_2"

    def test_valid_name_with_dollar(self):
        assert _validate_identifier("table$name") == "table$name"

    def test_rejects_semicolon_injection(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("users; DROP TABLE users--")

    def test_rejects_space(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("my table")

    def test_rejects_quote_injection(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("'; DROP TABLE users;--")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _validate_identifier("")


# ---------------------------------------------------------------------------
# URL builder
# ---------------------------------------------------------------------------


class TestBuildUrl:
    def test_mysql_url(self):
        info = {
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "username": "root",
            "password": "secret",
            "database": "mydb",
        }
        url = build_url(info)
        assert url.startswith("mysql+pymysql://root:secret@localhost:3306/mydb")

    def test_postgresql_url(self):
        info = {
            "db_type": "postgresql",
            "host": "db.example.com",
            "port": 5432,
            "username": "admin",
            "password": "p@ss!",
            "database": "app",
        }
        url = build_url(info)
        assert url.startswith("postgresql+psycopg2://admin:")
        assert "db.example.com:5432/app" in url

    def test_sqlite_url(self):
        info = {"db_type": "sqlite", "database": "/tmp/test.db"}
        url = build_url(info)
        assert url == "sqlite:////tmp/test.db"

    def test_sqlite_memory_url(self):
        info = {"db_type": "sqlite", "database": ":memory:"}
        url = build_url(info)
        assert url == "sqlite:///:memory:"

    def test_special_chars_encoded(self):
        """Passwords with special characters must be URL-encoded."""
        info = {
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "username": "user",
            "password": "p@ss/word=1",
            "database": "",
        }
        url = build_url(info)
        # The raw password must NOT appear verbatim in the URL
        assert "p@ss/word=1" not in url


# ---------------------------------------------------------------------------
# SQLite-backed functional tests
# ---------------------------------------------------------------------------

@pytest.fixture()
def sqlite_engine():
    """In-memory SQLite engine pre-populated with a test table."""
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER)"
        ))
        conn.execute(text(
            "INSERT INTO users (name, age) VALUES ('Alice', 30), ('Bob', 25), ('Carol', 35)"
        ))
    yield engine
    engine.dispose()


class TestListDatabases:
    def test_sqlite_returns_main(self, sqlite_engine):
        dbs = list_databases(sqlite_engine)
        assert dbs == ["main"]


class TestListTables:
    def test_finds_users_table(self, sqlite_engine):
        tables = list_tables(sqlite_engine)
        assert "users" in tables


class TestTableRowCount:
    def test_correct_count(self, sqlite_engine):
        count = table_row_count(sqlite_engine, "users")
        assert count == 3


class TestGetTableStructure:
    def test_returns_columns(self, sqlite_engine):
        cols = get_table_structure(sqlite_engine, "users")
        names = [c["name"] for c in cols]
        assert "id" in names
        assert "name" in names
        assert "age" in names

    def test_primary_key_flagged(self, sqlite_engine):
        cols = get_table_structure(sqlite_engine, "users")
        pk_cols = [c for c in cols if c["primary_key"]]
        assert any(c["name"] == "id" for c in pk_cols)


class TestBrowseTable:
    def test_returns_all_rows(self, sqlite_engine):
        columns, rows = browse_table(sqlite_engine, "users", page=1, page_size=10)
        assert "name" in columns
        assert len(rows) == 3

    def test_pagination(self, sqlite_engine):
        _, rows_p1 = browse_table(sqlite_engine, "users", page=1, page_size=2)
        _, rows_p2 = browse_table(sqlite_engine, "users", page=2, page_size=2)
        assert len(rows_p1) == 2
        assert len(rows_p2) == 1

    def test_empty_page_beyond_data(self, sqlite_engine):
        _, rows = browse_table(sqlite_engine, "users", page=99, page_size=10)
        assert rows == []


class TestExecuteQuery:
    def test_select_returns_rows(self, sqlite_engine):
        result = execute_query(sqlite_engine, "SELECT * FROM users")
        assert result["error"] is None
        assert result["rowcount"] == 3
        assert "name" in result["columns"]

    def test_insert_returns_rowcount(self, sqlite_engine):
        result = execute_query(sqlite_engine, "INSERT INTO users (name, age) VALUES ('Dave', 40)")
        assert result["error"] is None
        assert result["rowcount"] == 1

    def test_syntax_error_captured(self, sqlite_engine):
        result = execute_query(sqlite_engine, "SELEKT * FRUM users")
        assert result["error"] is not None
        assert result["rowcount"] == 0

    def test_max_rows_truncation(self, sqlite_engine):
        result = execute_query(sqlite_engine, "SELECT * FROM users", max_rows=2)
        assert result["truncated"] is True
        assert len(result["rows"]) == 2

    def test_make_engine_with_database_override(self):
        conn_info = {"db_type": "sqlite", "database": ":memory:"}
        engine = make_engine(conn_info, database=":memory:")
        assert engine is not None
        engine.dispose()
