"""Client-mode tests for Recall Blast Radius (checklist §6).

Skipped unless the shared ``lailara_engagement`` lib is installed. Fixtures are
generated on the fly — no client identifiers, no committed data.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

pytest.importorskip("lailara_engagement")

import client_mode  # noqa: E402

EDGES = pd.DataFrame([
    ("", "ING-1", "ingredient_lot"), ("ING-1", "B-1", "batch"),
    ("B-1", "FG-1", "fg_lot"), ("B-1", "FG-2", "fg_lot"),
], columns=["parent_lot_id", "child_lot_id", "child_type"])
SHIPTO = pd.DataFrame([
    ("FG-1", "Walmart", 100, 20), ("FG-2", "Kroger", 60, 5),
], columns=["fg_lot_id", "ship_to", "cases_in_channel", "cases_sold_through"])


def _write(d: Path, edges=EDGES, shipto=SHIPTO):
    gp, sp = d / "genealogy.csv", d / "shipto.csv"
    edges.to_csv(gp, index=False); shipto.to_csv(sp, index=False)
    return gp, sp


def _cfg(d: Path, seed="ING-1"):
    import yaml
    p = d / "engagement.demo.yml"
    p.write_text(yaml.safe_dump({
        "client": {"name": "Cinderhaven Provisions (demo)"}, "engagement": {"id": "T-1"},
        "as_of_date": "2025-12-27", "demo": True, "basis": {"seed_lot": seed}}), encoding="utf-8")
    return p


def _args(genealogy=None, shipto=None, seed=None):
    return SimpleNamespace(genealogy=genealogy, shipto=shipto, seed=seed)


def test_clean_trace_scopes_the_recall(tmp_path):
    gp, sp = _write(tmp_path)
    cfg = _cfg(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(gp), str(sp)))
    assert res["status"] == "ok"
    assert res["lots_affected"] == 2
    assert res["cases_in_channel"] == 160          # 100 + 60
    assert res["cost_high"] == round(160 * client_mode.COST_HIGH_PER_CASE, 2)
    assert res["n_notify"] == 2
    assert Path(res["report"]).is_file() and Path(res["exceptions_csv"]).is_file()


def test_deliverable_has_notification_list_and_draft(tmp_path):
    gp, sp = _write(tmp_path)
    cfg = _cfg(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(gp), str(sp)))
    html = Path(res["report"]).read_text(encoding="utf-8")
    assert "Walmart" in html and "Kroger" in html
    assert "Recall Blast Radius — Lot ING-1" in html
    assert "Seed lot" in html                       # provenance footer extra
    assert "DRAFT" in html


def test_missing_cases_in_channel_blocks(tmp_path):
    gp, sp = _write(tmp_path)
    pd.read_csv(sp).drop(columns=["cases_in_channel"]).to_csv(sp, index=False)
    cfg = _cfg(tmp_path)
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(gp), str(sp)))
    assert res["status"] == "blocked" and res["blocked_files"] == ["shipto"]


def test_seed_from_cli_overrides_config(tmp_path):
    gp, sp = _write(tmp_path)
    cfg = _cfg(tmp_path, seed="ING-1")
    res = client_mode.run(str(cfg), str(tmp_path / "out"), _args(str(gp), str(sp), seed="B-1"))
    assert res["status"] == "ok"
    assert res["lots_affected"] == 2               # B-1 still reaches FG-1, FG-2
