# symmetrical-couscous – PyDBA

> A stripped-down, Pythonic interpretation of phpMyAdmin. Simple. Fast. Effective.

![Login screen](https://github.com/user-attachments/assets/064b5e06-5054-40ba-b756-6445e9331271)

## Features

| Feature | Details |
|---|---|
| **Multi-database support** | MySQL / MariaDB, PostgreSQL, SQLite |
| **Database list** | Browse, create, and drop databases |
| **Table list** | See all tables with approximate row counts |
| **Browse data** | Paginated row viewer with NULL highlighting |
| **Table structure** | Column types, nullability, primary keys, indexes |
| **SQL editor** | Execute any SQL with Ctrl+Enter shortcut and handy snippets |
| **No stored credentials** | Connection info lives only in the HMAC-signed session cookie |

## Quick start

```bash
# Install
pip install -e .

# Run (development)
pydba

# Or with environment variables
PYDBA_HOST=0.0.0.0 PYDBA_PORT=8080 FLASK_ENV=production pydba
```

Open <http://127.0.0.1:5000> and fill in your database credentials.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `PYDBA_SECRET_KEY` | random | Flask secret key (set in production!) |
| `PYDBA_PAGE_SIZE` | `50` | Rows per page in the browser |
| `PYDBA_MAX_QUERY_ROWS` | `1000` | Maximum rows returned from a raw SQL query |
| `PYDBA_HOST` | `127.0.0.1` | Bind host |
| `PYDBA_PORT` | `5000` | Bind port |
| `FLASK_ENV` | `development` | `development` / `production` / `testing` |

## Architecture

```
pydba/
├── app.py          # Flask application factory
├── cli.py          # Entry-point (pydba command)
├── config.py       # Config classes (dev / test / prod)
├── db.py           # SQLAlchemy helpers – no ORM, plain SQL
├── routes/
│   ├── __init__.py # login_required decorator, shared engine helper
│   ├── auth.py     # /login, /logout
│   └── main.py     # /databases, /db/<db>, browse, structure, SQL editor
├── templates/      # Jinja2 + Bootstrap 5 templates
│   ├── base.html
│   ├── login.html
│   ├── databases.html
│   ├── tables.html
│   ├── browse.html
│   ├── structure.html
│   └── query.html
└── static/
    └── style.css
```

## Development

```bash
# Install with dev extras
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check pydba/ tests/
```

## Design philosophy

This is not a line-by-line Python port of phpMyAdmin. Instead it captures the **core workflow**:

1. Connect to a server
2. Pick a database
3. Browse / query its tables
4. Disconnect

Everything else (replication management, import/export wizards, user administration, stored procedure editors…) is intentionally left out. The goal is a tool you can audit in an afternoon and deploy with a single `pip install`.
