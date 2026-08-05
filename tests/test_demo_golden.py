"""Demo golden lock — Recall Blast Radius (client-mode trace engine).

Recall renders its demo scenarios from Postgres, so the deterministic lock here
is on the pure client-mode trace: a Scenario-B-shaped fixture (one shared
ingredient lot fanning out to multiple finished-goods lots across product lines)
run through the forward-trace scope. Blast radius scales with where in the BOM the
contamination sits, and that scaling is what this pins.

If an assertion fails, STOP: the trace engine drifted.
"""
from __future__ import annotations

import pandas as pd

from client_mode import COST_HIGH_PER_CASE, COST_LOW_PER_CASE, build_graph_from_edges, trace_scope

# Shared ingredient ING-1 -> two batches -> three fg lots; a second ingredient
# ING-2 -> its own fg lot (must NOT be pulled in by an ING-1 recall).
EDGES = pd.DataFrame([
    ("", "ING-1", "ingredient_lot"),
    ("", "ING-2", "ingredient_lot"),
    ("ING-1", "B-1", "batch"),
    ("ING-1", "B-2", "batch"),
    ("B-1", "FG-1", "fg_lot"),
    ("B-1", "FG-2", "fg_lot"),
    ("B-2", "FG-3", "fg_lot"),
    ("ING-2", "B-9", "batch"),
    ("B-9", "FG-9", "fg_lot"),
], columns=["parent_lot_id", "child_lot_id", "child_type"])

SHIPTO = pd.DataFrame([
    ("FG-1", "Walmart", 100, 20),
    ("FG-1", "Kroger", 50, 5),
    ("FG-2", "Costco", 80, 10),
    ("FG-3", "Sprouts", 40, 30),
    ("FG-9", "Whole Foods", 999, 0),   # from ING-2 — out of scope for an ING-1 recall
], columns=["fg_lot_id", "ship_to", "cases_in_channel", "cases_sold_through"])


def test_shared_ingredient_scope_is_pinned():
    G = build_graph_from_edges(EDGES)
    scope = trace_scope(G, SHIPTO, "ING-1")
    assert scope["lots_affected"] == 3                       # FG-1, FG-2, FG-3 (not FG-9)
    assert scope["cases_in_channel"] == 270                  # 100+50+80+40, not the 999 from ING-2
    assert scope["cost_low"] == round(270 * COST_LOW_PER_CASE, 2)
    assert scope["cost_high"] == round(270 * COST_HIGH_PER_CASE, 2)
    assert scope["notification_list"] == ["Costco", "Kroger", "Sprouts", "Walmart"]  # not Whole Foods


def test_single_fg_lot_scope_is_smaller():
    # Blast radius scales with BOM position: seeding a single batch is bounded.
    G = build_graph_from_edges(EDGES)
    scope = trace_scope(G, SHIPTO, "B-2")
    assert scope["lots_affected"] == 1                       # only FG-3
    assert scope["cases_in_channel"] == 40


def test_unknown_seed_yields_empty_scope():
    G = build_graph_from_edges(EDGES)
    scope = trace_scope(G, SHIPTO, "NOPE")
    assert scope["lots_affected"] == 0
    assert scope["cases_in_channel"] == 0
    assert scope["notification_list"] == []
