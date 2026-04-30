"""Flask application factory for PyDBA."""

from __future__ import annotations

from flask import Flask

from pydba.config import get_config
from pydba.extension import _register_context_processor, pydba_assets_bp
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
    app = Flask(__name__, template_folder="templates", static_folder=None)
    cfg = get_config(env)
    app.config.from_object(cfg)

    # Register blueprints
    app.register_blueprint(pydba_assets_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    _register_context_processor(app)

    return app
