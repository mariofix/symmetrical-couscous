"""Route helpers shared across blueprints."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import redirect, session, url_for

from pydba.db import make_engine


def get_engine(database: str | None = None):
    """Return an engine built from the current session's connection info."""
    conn_info = session.get("conn_info")
    if not conn_info:
        return None
    return make_engine(conn_info, database=database)


def login_required(f: Callable) -> Callable:
    """Decorator that redirects to the login page if not connected."""

    @wraps(f)
    def decorated(*args: Any, **kwargs: Any):
        if "conn_info" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated
