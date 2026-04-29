"""Authentication routes – connect to / disconnect from a database server."""

from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from pydba.db import list_databases, make_engine

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def index():
    if "conn_info" in session:
        return redirect(url_for("main.databases"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn_info = {
            "db_type": request.form.get("db_type", "mysql"),
            "host": request.form.get("host", "localhost").strip(),
            "port": int(
                request.form.get("port") or _default_port(request.form.get("db_type", "mysql"))
            ),
            "username": request.form.get("username", "").strip(),
            "password": request.form.get("password", ""),
            "database": request.form.get("database", "").strip(),
        }
        # Validate connection
        try:
            engine = make_engine(conn_info)
            list_databases(engine)
            engine.dispose()
        except Exception as exc:  # noqa: BLE001
            flash(f"Connection failed: {exc}", "danger")
            return render_template("login.html", form=conn_info)

        session["conn_info"] = conn_info
        flash("Connected successfully.", "success")
        return redirect(url_for("main.databases"))

    return render_template("login.html", form={})


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Disconnected.", "info")
    return redirect(url_for("auth.login"))


def _default_port(db_type: str) -> int:
    return {"mysql": 3306, "postgresql": 5432}.get(db_type, 3306)
