from fastapi.testclient import TestClient
import os
from pathlib import Path
import subprocess
import sys

from dashboard.plugin_api import router
from fastapi import FastAPI


def test_dashboard_routes_are_json():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get("/state")
    assert response.status_code == 200
    assert "stats" in response.json()


def test_dashboard_api_loads_through_hermes_file_loader():
    repo_root = Path(__file__).parents[3]
    api_path = Path(__file__).parents[1] / "dashboard" / "plugin_api.py"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)
    result = subprocess.run(
        [sys.executable, "-c", "from hermes_cli.plugin_isolation import import_user_code; import_user_code(__import__('pathlib').Path(__import__('sys').argv[1]), 'hermes_dashboard_plugin_repro')", str(api_path)],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
