from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_missing_audit_returns_404():
    response = client.get(
        "/audits/not-a-real-audit-id"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Audit not found."