"""Flask extension entry-point for PyDBA.

Typical usage – embed PyDBA in an existing Flask application::

    from flask import Flask
    from pydba import PyDBA

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-me"

    # Optional: auto-connect from an existing SQLAlchemy URI so the login
    # form is skipped entirely.
    # app.config["PYDBA_DATABASE_URI"] = "sqlite:///dev.db"
    # or use the standard Flask-SQLAlchemy key:
    # app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://user:pass@host/db"

    pydba = PyDBA()
    pydba.init_app(app)

    if __name__ == "__main__":
        app.run()

PyDBA will be available at ``/pydba`` by default.  Change the mount prefix
with ``app.config["PYDBA_URL_PREFIX"]`` or by passing *url_prefix* to
:meth:`PyDBA.init_app`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from flask import Blueprint, current_app, session

if TYPE_CHECKING:
    from flask import Flask

# ---------------------------------------------------------------------------
# Blueprint that serves PyDBA's own static assets and templates.
# Registering it gives embedded apps access to both without copying files.
# Templates reference the static folder via ``url_for("pydba_assets.static")``.
# ---------------------------------------------------------------------------

pydba_assets_bp = Blueprint(
    "pydba_assets",
    __name__,
    static_folder="static",
    static_url_path="/pydba/static",
    template_folder="templates",
)


# ---------------------------------------------------------------------------
# Internal helpers used by both create_app() and PyDBA.init_app()
# ---------------------------------------------------------------------------


def _register_context_processor(app: Flask) -> None:
    """Register the sidebar context processor on *app*."""

    @app.context_processor
    def inject_sidebar_data() -> dict:
        from pydba.db import list_databases, list_tables, make_engine

        conn_info = session.get("conn_info")
        if not conn_info:
            return {}

        sidebar_databases: list[str] = []
        try:
            engine = make_engine(conn_info)
            sidebar_databases = list_databases(engine)
            engine.dispose()
        except Exception:  # noqa: BLE001
            pass

        selected_db: str | None = session.get("selected_db")
        sidebar_tables: list[str] = []
        if selected_db:
            try:
                engine = make_engine(conn_info, database=selected_db)
                sidebar_tables = list_tables(engine)
                engine.dispose()
            except Exception:  # noqa: BLE001
                pass

        return {
            "sidebar_databases": sidebar_databases,
            "sidebar_tables": sidebar_tables,
            "selected_db": selected_db,
        }


def _register_auto_connect(app: Flask) -> None:
    """Register a before-request hook that auto-populates *conn_info* in the
    session when ``PYDBA_DATABASE_URI`` or ``SQLALCHEMY_DATABASE_URI`` is
    present in the application config.

    This lets developers skip the login form entirely when PyDBA is embedded
    in an application that already has a database URI configured.
    """

    @app.before_request
    def _pydba_auto_connect() -> None:
        if "conn_info" not in session:
            uri = current_app.config.get("PYDBA_DATABASE_URI") or current_app.config.get(
                "SQLALCHEMY_DATABASE_URI"
            )
            if uri:
                from pydba.db import parse_sqlalchemy_url

                session["conn_info"] = parse_sqlalchemy_url(uri)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class PyDBA:
    """Flask extension that mounts PyDBA on an existing Flask application.

    Parameters
    ----------
    app:
        If supplied, :meth:`init_app` is called immediately.
    url_prefix:
        URL prefix used when ``app.config`` does not contain
        ``PYDBA_URL_PREFIX``.  Defaults to ``"/pydba"``.

    Example::

        # Application factory pattern
        pydba = PyDBA()

        def create_app():
            app = Flask(__name__)
            app.config.from_object(...)
            pydba.init_app(app)
            return app
    """

    def __init__(self, app: Flask | None = None, url_prefix: str = "/pydba") -> None:
        self._url_prefix = url_prefix
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask, url_prefix: str | None = None) -> None:
        """Register PyDBA blueprints and helpers on *app*.

        Parameters
        ----------
        app:
            The Flask application to configure.
        url_prefix:
            URL prefix for PyDBA routes.  Falls back (in order) to
            ``app.config["PYDBA_URL_PREFIX"]``, then to the value passed to
            :class:`PyDBA.__init__` (default ``"/pydba"``).
        """
        from pydba.routes.auth import auth_bp
        from pydba.routes.main import main_bp

        prefix = url_prefix or app.config.get("PYDBA_URL_PREFIX") or self._url_prefix

        app.register_blueprint(pydba_assets_bp)
        app.register_blueprint(auth_bp, url_prefix=prefix)
        app.register_blueprint(main_bp, url_prefix=prefix)

        _register_context_processor(app)
        _register_auto_connect(app)


def init_app(app: Flask, url_prefix: str = "/pydba") -> None:
    """Convenience function – equivalent to ``PyDBA(app, url_prefix)``.

    Parameters
    ----------
    app:
        The Flask application to configure.
    url_prefix:
        URL prefix for PyDBA routes (default ``"/pydba"``).
    """
    PyDBA(app, url_prefix=url_prefix)
