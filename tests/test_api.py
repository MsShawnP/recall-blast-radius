"""
API-layer tests — routing and validation paths that need no live database.

The trace 404 path mocks api.routers.trace.get_conn; /api/scenarios reads the
committed pipeline/cache/scenario_graphs.json.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_trace_backward_direction_rejected():
    resp = client.post("/api/trace", json={"lot_id": "ING-001", "direction": "backward"})
    assert resp.status_code == 400


def test_trace_invalid_direction_rejected_by_schema():
    resp = client.post("/api/trace", json={"lot_id": "ING-001", "direction": "sideways"})
    assert resp.status_code == 422


def test_trace_unknown_lot_404():
    mock_conn = MagicMock()
    cur = mock_conn.cursor.return_value
    cur.fetchall.return_value = []   # no fct_blast_radius rows
    cur.fetchone.return_value = None  # not a packaging lot either
    with patch("api.routers.trace.get_conn", return_value=mock_conn):
        resp = client.post("/api/trace", json={"lot_id": "NOPE-999"})
    assert resp.status_code == 404
    mock_conn.close.assert_called_once()


def test_scenarios_served_from_cache():
    resp = client.get("/api/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert {s["id"] for s in data} == {"A", "B", "C"}
    for s in data:
        assert s["result"]["nodes"], f"scenario {s['id']} has no nodes"
        assert "cases_in_channel" in s["result"]["scope"]
