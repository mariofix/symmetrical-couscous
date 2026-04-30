"""Unit tests for the Flask application routes."""

from __future__ import annotations


class TestAuth:
    def test_root_redirects_to_login(self, client):
        """GET / with no session should redirect to /login."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_login_page_renders(self, client):
        """GET /login should return a 200 with a form."""
        response = client.get("/login")
        assert response.status_code == 200
        assert b"Connect to a Database Server" in response.data

    def test_logout_clears_session(self, auth_client):
        """GET /logout should clear the session and redirect to login."""
        response = auth_client.get("/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]
        with auth_client.session_transaction() as sess:
            assert "conn_info" not in sess

    def test_login_with_sqlite_in_memory(self, client):
        """Logging in with an SQLite in-memory database should succeed."""
        response = client.post(
            "/login",
            data={
                "db_type": "sqlite",
                "host": "",
                "port": "",
                "username": "",
                "password": "",
                "database": ":memory:",
            },
            follow_redirects=False,
        )
        # Successful login redirects to /databases
        assert response.status_code == 302
        assert "/databases" in response.headers["Location"]

    def test_login_with_bad_mysql_fails(self, client):
        """Logging in with bad MySQL credentials should show an error."""
        response = client.post(
            "/login",
            data={
                "db_type": "mysql",
                "host": "127.0.0.1",
                "port": "3306",
                "username": "nonexistent",
                "password": "wrongpassword",
                "database": "",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Connection failed" in response.data


class TestProtectedRoutes:
    def test_databases_requires_login(self, client):
        """GET /databases without a session should redirect to login."""
        response = client.get("/databases", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_databases_renders_for_authenticated(self, auth_client):
        """GET /databases with a valid session should render database list."""
        response = auth_client.get("/databases")
        assert response.status_code == 200
        assert b"Databases" in response.data

    def test_query_page_renders(self, auth_client):
        """GET /db/<db>/query should render the SQL editor."""
        response = auth_client.get("/db/main/query")
        assert response.status_code == 200
        assert b"SQL Query" in response.data
        assert b"sql-editor" in response.data

    def test_tables_page_renders(self, auth_client):
        """GET /db/<db> should render the tables list."""
        response = auth_client.get("/db/main")
        assert response.status_code == 200
        assert b"main" in response.data

    def test_create_database_requires_login(self, client):
        """POST /databases/create without login should redirect."""
        response = client.post("/databases/create", data={"name": "foo"})
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]
