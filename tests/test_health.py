from backend.app.main import health_check


def test_health_check():
    result = health_check()
    assert result["status"] == "healthy"
    assert "storage_provider" in result
    assert "environment" in result
