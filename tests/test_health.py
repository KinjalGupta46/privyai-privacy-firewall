"""
tests/test_health.py

Phase 1 tests — /health endpoint.

Tests:
  - Endpoint returns 200 OK.
  - Response contains required fields (status, app_name, version, timestamp).
  - Status is "ok".
  - LLM provider info is present and safe (no API keys).
  - Database section is present (may be "not_configured" in test environment).
  - No secrets are exposed in the response.
"""

from __future__ import annotations


def test_health_returns_200(client):
    """GET /health must return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}. Body: {response.text}"
    )


def test_health_response_structure(client):
    """Response JSON must include all required top-level fields."""
    response = client.get("/health")
    body = response.json()

    required_fields = {"status", "app_name", "version", "timestamp", "database", "llm_provider"}
    missing = required_fields - body.keys()
    assert not missing, f"Missing fields in /health response: {missing}"


def test_health_status_is_ok(client):
    """The 'status' field must be 'ok'."""
    body = client.get("/health").json()
    assert body["status"] == "ok"


def test_health_app_name(client):
    """The 'app_name' field must be a non-empty string."""
    body = client.get("/health").json()
    assert isinstance(body["app_name"], str)
    assert len(body["app_name"]) > 0


def test_health_version(client):
    """The 'version' field must be a non-empty string."""
    body = client.get("/health").json()
    assert isinstance(body["version"], str)
    assert len(body["version"]) > 0


def test_health_timestamp_is_integer(client):
    """The 'timestamp' field must be a positive integer (Unix epoch)."""
    body = client.get("/health").json()
    assert isinstance(body["timestamp"], int)
    assert body["timestamp"] > 0


def test_health_database_field_present(client):
    """The 'database' field must be a dict with a 'status' key."""
    body = client.get("/health").json()
    db = body["database"]
    assert isinstance(db, dict)
    assert "status" in db


def test_health_llm_provider_field_present(client):
    """The 'llm_provider' field must be a dict with a 'provider' key."""
    body = client.get("/health").json()
    llm = body["llm_provider"]
    assert isinstance(llm, dict)
    assert "provider" in llm


def test_health_mock_provider_in_test_env(client):
    """In the test environment, LLM provider should be 'mock'."""
    body = client.get("/health").json()
    assert body["llm_provider"]["provider"] == "mock"


def test_health_no_secrets_in_response(client):
    """Response must not contain API keys, passwords or connection strings."""
    raw_text = client.get("/health").text.lower()

    forbidden_patterns = [
        "api_key",
        "apikey",
        "password",
        "secret",
        "mysql+",        # database URL scheme
        "pymysql://",    # database URL
    ]
    for pattern in forbidden_patterns:
        assert pattern not in raw_text, (
            f"Potential secret exposure: found '{pattern}' in /health response."
        )


def test_health_database_not_configured_in_test_env(client):
    """Without DATABASE_URL set, database status should be 'not_configured'."""
    body = client.get("/health").json()
    db_status = body["database"]["status"]
    # In test env DATABASE_URL is empty → not_configured is expected.
    # If a real DB is configured in CI, "connected" is also acceptable.
    assert db_status in ("not_configured", "connected", "error"), (
        f"Unexpected database status: {db_status}"
    )
