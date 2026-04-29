"""Main application routes – databases, tables, browsing, structure, SQL."""

from __future__ import annotations

import math

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from pydba.db import (
    _validate_identifier,
    browse_table,
    execute_query,
    get_table_indexes,
    get_table_structure,
    list_databases,
    list_tables,
    make_engine,
    table_row_count,
)
from pydba.routes import login_required

main_bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Database list
# ---------------------------------------------------------------------------


@main_bp.route("/databases")
@login_required
def databases():
    engine = make_engine(session["conn_info"])
    try:
        dbs = list_databases(engine)
    except Exception as exc:  # noqa: BLE001
        flash(f"Error listing databases: {exc}", "danger")
        dbs = []
    finally:
        engine.dispose()

    conn = session["conn_info"]
    return render_template(
        "databases.html",
        databases=dbs,
        conn=conn,
    )


# ---------------------------------------------------------------------------
# Table list for a database
# ---------------------------------------------------------------------------


@main_bp.route("/db/<database>")
@login_required
def tables(database: str):
    engine = make_engine(session["conn_info"], database=database)
    try:
        tbl_names = list_tables(engine)
        tbl_info = []
        for t in tbl_names:
            try:
                count = table_row_count(engine, t)
            except Exception:  # noqa: BLE001
                count = "?"
            tbl_info.append({"name": t, "rows": count})
    except Exception as exc:  # noqa: BLE001
        flash(f"Error listing tables: {exc}", "danger")
        tbl_info = []
    finally:
        engine.dispose()

    return render_template(
        "tables.html",
        database=database,
        tables=tbl_info,
    )


# ---------------------------------------------------------------------------
# Browse table rows
# ---------------------------------------------------------------------------


@main_bp.route("/db/<database>/table/<table>/browse")
@login_required
def browse(database: str, table: str):
    page = int(request.args.get("page", 1))
    page_size = current_app.config["PAGE_SIZE"]

    engine = make_engine(session["conn_info"], database=database)
    try:
        total = table_row_count(engine, table)
        columns, rows = browse_table(engine, table, page=page, page_size=page_size)
    except Exception as exc:  # noqa: BLE001
        flash(f"Error browsing table: {exc}", "danger")
        columns, rows, total = [], [], 0
    finally:
        engine.dispose()

    total_pages = max(1, math.ceil(total / page_size)) if total else 1

    return render_template(
        "browse.html",
        database=database,
        table=table,
        columns=columns,
        rows=rows,
        page=page,
        total_pages=total_pages,
        total_rows=total,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Table structure
# ---------------------------------------------------------------------------


@main_bp.route("/db/<database>/table/<table>/structure")
@login_required
def structure(database: str, table: str):
    engine = make_engine(session["conn_info"], database=database)
    try:
        columns = get_table_structure(engine, table)
        indexes = get_table_indexes(engine, table)
    except Exception as exc:  # noqa: BLE001
        flash(f"Error reading structure: {exc}", "danger")
        columns, indexes = [], []
    finally:
        engine.dispose()

    return render_template(
        "structure.html",
        database=database,
        table=table,
        columns=columns,
        indexes=indexes,
    )


# ---------------------------------------------------------------------------
# SQL query editor
# ---------------------------------------------------------------------------


@main_bp.route("/db/<database>/query", methods=["GET", "POST"])
@login_required
def query(database: str):
    sql = ""
    result = None

    if request.method == "POST":
        sql = request.form.get("sql", "").strip()
        if sql:
            engine = make_engine(session["conn_info"], database=database)
            try:
                result = execute_query(engine, sql, max_rows=current_app.config["MAX_QUERY_ROWS"])
            finally:
                engine.dispose()

    return render_template(
        "query.html",
        database=database,
        sql=sql,
        result=result,
    )


# ---------------------------------------------------------------------------
# Drop table (POST only)
# ---------------------------------------------------------------------------


@main_bp.route("/db/<database>/table/<table>/drop", methods=["POST"])
@login_required
def drop_table(database: str, table: str):
    try:
        _validate_identifier(table)
        _validate_identifier(database)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.tables", database=database))

    engine = make_engine(session["conn_info"], database=database)
    try:
        result = execute_query(engine, f"DROP TABLE `{table}`")
        if result["error"]:
            flash(f"Error dropping table: {result['error']}", "danger")
        else:
            flash(f"Table '{table}' dropped.", "success")
    finally:
        engine.dispose()
    return redirect(url_for("main.tables", database=database))


# ---------------------------------------------------------------------------
# Create database / drop database
# ---------------------------------------------------------------------------


@main_bp.route("/databases/create", methods=["POST"])
@login_required
def create_database():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Database name is required.", "warning")
        return redirect(url_for("main.databases"))

    try:
        _validate_identifier(name)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.databases"))

    engine = make_engine(session["conn_info"])
    try:
        result = execute_query(engine, f"CREATE DATABASE `{name}`")
        if result["error"]:
            flash(f"Error: {result['error']}", "danger")
        else:
            flash(f"Database '{name}' created.", "success")
    finally:
        engine.dispose()
    return redirect(url_for("main.databases"))


@main_bp.route("/databases/<database>/drop", methods=["POST"])
@login_required
def drop_database(database: str):
    try:
        _validate_identifier(database)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("main.databases"))

    engine = make_engine(session["conn_info"])
    try:
        result = execute_query(engine, f"DROP DATABASE `{database}`")
        if result["error"]:
            flash(f"Error: {result['error']}", "danger")
        else:
            flash(f"Database '{database}' dropped.", "success")
    finally:
        engine.dispose()
    return redirect(url_for("main.databases"))
