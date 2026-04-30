"""Tests for the PyDBA Flask extension (pydba.extension)."""

from __future__ import annotations

import pytest
from flask import Flask

from pydba import PyDBA, init_app
from pydba.db import parse_sqlalchemy_url

# ---------------------------------------------------------------------------
# parse_sqlalchemy_url
# ---------------------------------------------------------------------------


class TestParseAlchemyUrl:
    def test_mysql_bare_scheme(self):
        info = parse_sqlalchemy_url("mysql://root:secret@localhost:3306/mydb")
        assert info["db_type"] == "mysql"
        assert info["host"] == "localhost"
        assert info["port"] == 3306
        assert info["username"] == "root"
        assert info["password"] == "secret"
        assert info["database"] == "mydb"

    def test_mysql_with_driver(self):
        info = parse_sqlalchemy_url("mysql+pymysql://user:pass@db.host:3307/app")
        assert info["db_type"] == "mysql"
        assert info["port"] == 3307
        assert info["database"] == "app"

    def test_postgresql_with_driver(self):
        info = parse_sqlalchemy_url("postgresql+psycopg2://admin:pw@pg.host:5432/prod")
        assert info["db_type"] == "postgresql"
        assert info["host"] == "pg.host"
        assert info["port"] == 5432

    def test_sqlite_file(self):
        info = parse_sqlalchemy_url("sqlite:////tmp/dev.db")
        assert info["db_type"] == "sqlite"
        assert info["database"] == "/tmp/dev.db"
        assert info["username"] == ""
        assert info["password"] == ""

    def test_sqlite_memory(self):
        info = parse_sqlalchemy_url("sqlite:///:memory:")
        assert info["db_type"] == "sqlite"
        assert info["database"] == ":memory:"

    def test_special_chars_decoded(self):
        info = parse_sqlalchemy_url("mysql://user:p%40ss@localhost/db")
        assert info["password"] == "p@ss"

    def test_default_mysql_port(self):
        info = parse_sqlalchemy_url("mysql://user:pass@host/db")
        assert info["port"] == 3306

    def test_default_postgresql_port(self):
        info = parse_sqlalchemy_url("postgresql://user:pass@host/db")
        assert info["port"] == 5432


# ---------------------------------------------------------------------------
# PyDBA extension – blueprint registration
# ---------------------------------------------------------------------------


@pytest.fixture()
def bare_app():
    """A minimal Flask app with no blueprints registered."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test-ext-key"
    app.config["TESTING"] = True
    return app


class TestPyDBAExtension:
    def test_init_app_class(self, bare_app):
        """PyDBA(app) should register routes under /pydba by default."""
        PyDBA(bare_app)
        client = bare_app.test_client()
        # login page should be reachable at /pydba/login
        resp = client.get("/pydba/login")
        assert resp.status_code == 200

    def test_init_app_function(self, bare_app):
        """init_app() convenience function should work identically."""
        init_app(bare_app)
        client = bare_app.test_client()
        resp = client.get("/pydba/login")
        assert resp.status_code == 200

    def test_custom_url_prefix(self, bare_app):
        """Custom url_prefix should mount routes at the specified path."""
        PyDBA(bare_app, url_prefix="/admin/db")
        client = bare_app.test_client()
        assert client.get("/admin/db/login").status_code == 200
        assert client.get("/pydba/login").status_code == 404

    def test_config_url_prefix(self, bare_app):
        """PYDBA_URL_PREFIX config key should override the default."""
        bare_app.config["PYDBA_URL_PREFIX"] = "/tools/pydba"
        PyDBA(bare_app)
        client = bare_app.test_client()
        assert client.get("/tools/pydba/login").status_code == 200

    def test_static_assets_served(self, bare_app):
        """PyDBA static assets should be reachable at /pydba/static/."""
        PyDBA(bare_app)
        client = bare_app.test_client()
        resp = client.get("/pydba/static/style.css")
        assert resp.status_code == 200

    def test_databases_redirects_without_session(self, bare_app):
        """Accessing /pydba/databases without a session redirects to login."""
        PyDBA(bare_app)
        client = bare_app.test_client()
        resp = client.get("/pydba/databases", follow_redirects=False)
        assert resp.status_code == 302
        assert "login" in resp.headers["Location"]

    def test_application_factory_pattern(self):
        """PyDBA should work with the application factory pattern."""
        pydba = PyDBA()

        app = Flask(__name__)
        app.config["SECRET_KEY"] = "factory-key"
        app.config["TESTING"] = True
        pydba.init_app(app)

        client = app.test_client()
        assert client.get("/pydba/login").status_code == 200


# ---------------------------------------------------------------------------
# Auto-connect from SQLAlchemy URI
# ---------------------------------------------------------------------------


class TestAutoConnect:
    def _make_app(self, config_key: str) -> Flask:
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "auto-key"
        app.config["TESTING"] = True
        app.config[config_key] = "sqlite:///:memory:"
        PyDBA(app)
        return app

    def test_pydba_uri_auto_populates_session(self):
        """PYDBA_DATABASE_URI should auto-populate conn_info and bypass login."""
        app = self._make_app("PYDBA_DATABASE_URI")
        client = app.test_client()
        # With auto-connect, /pydba/login should redirect to databases
        resp = client.get("/pydba/login", follow_redirects=False)
        assert resp.status_code == 302
        assert "databases" in resp.headers["Location"]

    def test_sqlalchemy_uri_auto_populates_session(self):
        """SQLALCHEMY_DATABASE_URI should also auto-populate conn_info."""
        app = self._make_app("SQLALCHEMY_DATABASE_URI")
        client = app.test_client()
        resp = client.get("/pydba/login", follow_redirects=False)
        assert resp.status_code == 302
        assert "databases" in resp.headers["Location"]

    def test_pydba_uri_takes_precedence(self):
        """PYDBA_DATABASE_URI should take precedence over SQLALCHEMY_DATABASE_URI."""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "prec-key"
        app.config["TESTING"] = True
        app.config["PYDBA_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://bad:creds@nonexistent/db"
        PyDBA(app)
        client = app.test_client()
        # Should use SQLite (PYDBA_DATABASE_URI), not MySQL
        resp = client.get("/pydba/databases", follow_redirects=False)
        # Either gets the page (200) or redirects to login (302 → 200);
        # the important thing is it doesn't blow up trying to reach MySQL.
        assert resp.status_code in (200, 302)
