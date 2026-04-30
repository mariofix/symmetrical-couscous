"""CLI entry-point for PyDBA."""

from __future__ import annotations

import os

from pydba.app import create_app


def main() -> None:
    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env)
    host = os.environ.get("PYDBA_HOST", "127.0.0.1")
    port = int(os.environ.get("PYDBA_PORT", "5000"))
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
