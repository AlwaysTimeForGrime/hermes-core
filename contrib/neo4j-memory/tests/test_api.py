from fastapi.testclient import TestClient

from dashboard.plugin_api import router
from fastapi import FastAPI


def test_dashboard_routes_are_json():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/state")
    assert response.status_code == 200
    assert "stats" in response.json()
