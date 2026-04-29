"""Shared pytest fixtures for PyDBA tests."""

from __future__ import annotations

import pytest

from pydba.app import create_app


@pytest.fixture()
def app():
    """Create a testing Flask application."""
    application = create_app("testing")
    yield application


@pytest.fixture()
def client(app):
    """Return a test client for the Flask application."""
    return app.test_client()


@pytest.fixture()
def auth_client(client):
    """Return a test client that has an active (SQLite in-memory) session."""
    with client.session_transaction() as sess:
        sess["conn_info"] = {
            "db_type": "sqlite",
            "host": "",
            "port": 0,
            "username": "",
            "password": "",
            "database": ":memory:",
        }
    return client
