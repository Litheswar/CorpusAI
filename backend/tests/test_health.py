def test_health_check_endpoint(client):
    """Verifies that the public health check endpoint returns 200 OK and expected structure."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.get_json()
    assert data is not None
    assert data["status"] == "ok"
    assert data["service"] == "corpusai-api"

    # Verify no secrets or sensitive configs are leaked
    body_str = response.get_data(as_text=True).lower()
    assert "secret" not in body_str
    assert "service_role" not in body_str
    assert "postgres" not in body_str
