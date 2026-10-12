"""Require both the agent backend and the unified web listener to be ready."""

import json
import urllib.request


with urllib.request.urlopen("http://127.0.0.1:18000/health", timeout=5) as response:
    assert json.load(response)["status"] == "ok"
with urllib.request.urlopen("http://127.0.0.1:8000/canvas/", timeout=5) as response:
    assert response.status == 200
    assert "text/html" in response.headers.get("Content-Type", "")
