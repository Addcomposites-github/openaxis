"""Shared fixtures for backend service tests.

Uses FastAPI TestClient to test endpoints without starting a real server.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure backend and openaxis are importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


@pytest.fixture
def client():
    """Create a FastAPI TestClient with the OpenAxis app."""
    from backend.server import app

    return TestClient(app)


@pytest.fixture
def sample_toolpath_data():
    """Minimal valid toolpath data dict."""
    return {
        "id": "test_tp_001",
        "totalLayers": 2,
        "layerHeight": 0.3,
        "processType": "waam",
        "statistics": {
            "totalPoints": 6,
            "totalSegments": 2,
            "layerCount": 2,
            "estimatedTime": 10,
            "estimatedMaterial": 50,
        },
        "segments": [
            {
                "type": "perimeter",
                "layer": 0,
                "speed": 1000.0,
                "extrusionRate": 1.0,
                "points": [[10.0, 20.0, 0.0], [30.0, 20.0, 0.0], [30.0, 40.0, 0.0]],
            },
            {
                "type": "perimeter",
                "layer": 1,
                "speed": 1000.0,
                "extrusionRate": 1.0,
                "points": [[10.0, 20.0, 0.3], [30.0, 20.0, 0.3], [30.0, 40.0, 0.3]],
            },
        ],
    }


@pytest.fixture
def seeded_toolpath(client, sample_toolpath_data):
    """Store a toolpath in app state and return its ID."""
    from backend.server import state

    state.toolpaths[sample_toolpath_data["id"]] = sample_toolpath_data
    yield sample_toolpath_data["id"]
    state.toolpaths.pop(sample_toolpath_data["id"], None)
