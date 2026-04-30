"""Flask application factory for PyDBA."""

from __future__ import annotations

from flask import Flask, session

from pydba.config import get_config
from pydba.routes.auth import auth_bp
from pydba.routes.main import main_bp


def create_app(env: str | None = None) -> Flask:
    """Create and configure the Flask application.

    Parameters
    ----------
    env:
        One of ``'development'``, ``'testing'``, or ``'production'``.
        Falls back to the ``FLASK_ENV`` environment variable, then
        ``'development'``.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    cfg = get_config(env)
    app.config.from_object(cfg)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_sidebar_data() -> dict:
        """Inject databases list and tables list into every template context."""
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

    return app
