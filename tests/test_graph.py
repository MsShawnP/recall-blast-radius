"""
Unit tests for the recall graph logic (pipeline/graph.py).

No DB required — every function under test here is pure graph/dict
manipulation. DB-touching functions (packaging_lot_rows, packaging_lot_scope)
are exercised via the API layer with a live database, not here.
"""
import networkx as nx

from pipeline.graph import (
    AGGREGATE_THRESHOLD,
    _empty_scope,
    aggregate_shipments,
    build_graph,
    graph_to_api_format,
    scope_row_to_panel,
    subgraph_for_root,
)

# rows: (root_lot_id, node_type, node_id, label, depth, parent_id)
CHAIN_ROWS = [
    ("ING-001", "ingredient_lot", "ING-001", "Organic almonds", 0, None),
    ("ING-001", "batch", "B-100", "BATCH-100", 1, "ING-001"),
    ("ING-001", "fg_lot", "FG-200", "LOT-200", 2, "B-100"),
    ("ING-001", "shipment", "SH-300", "2026-05-01", 3, "FG-200"),
    ("ING-001", "retailer", "RET-1", "Walmart", 4, "SH-300"),
]


def test_build_graph_nodes_and_edges():
    G = build_graph(CHAIN_ROWS)
    assert set(G.nodes) == {"ING-001", "B-100", "FG-200", "SH-300", "RET-1"}
    assert list(nx.shortest_path(G, "ING-001", "RET-1")) == [
        "ING-001", "B-100", "FG-200", "SH-300", "RET-1"
    ]
    assert G.nodes["B-100"]["type"] == "batch"
    assert G.nodes["RET-1"]["label"] == "Walmart"
    assert G.nodes["ING-001"]["depth"] == 0


def test_build_graph_root_has_no_inbound_edge():
    G = build_graph(CHAIN_ROWS)
    assert G.in_degree("ING-001") == 0


def test_build_graph_coerces_label_to_str():
    rows = [("R", "ingredient_lot", "R", 12345, 0, None)]
    G = build_graph(rows)
    assert G.nodes["R"]["label"] == "12345"


def test_subgraph_for_root_excludes_unrelated_branch():
    rows = CHAIN_ROWS + [
        ("ING-002", "ingredient_lot", "ING-002", "Sea salt", 0, None),
        ("ING-002", "batch", "B-999", "BATCH-999", 1, "ING-002"),
    ]
    G = build_graph(rows)
    sub = subgraph_for_root(G, "ING-001")
    assert set(sub.nodes) == {"ING-001", "B-100", "FG-200", "SH-300", "RET-1"}


def test_subgraph_for_missing_root_is_empty():
    G = build_graph(CHAIN_ROWS)
    sub = subgraph_for_root(G, "NOPE")
    assert len(sub.nodes) == 0


def _fan_out_graph(n_shipments: int) -> nx.DiGraph:
    """fg_lot FG-1 ships n shipments; 2/3 go to RET-A, 1/3 to RET-B."""
    rows = [("ING", "fg_lot", "FG-1", "LOT-1", 0, None)]
    for i in range(n_shipments):
        ship = f"SH-{i}"
        ret = "RET-A" if i % 3 else "RET-B"
        rows.append(("ING", "shipment", ship, f"2026-05-{i:02d}", 1, "FG-1"))
        rows.append(("ING", "retailer", ret, ret, 2, ship))
    return build_graph(rows)


def test_aggregate_shipments_below_threshold_is_untouched():
    G = _fan_out_graph(AGGREGATE_THRESHOLD)  # exactly at threshold → no collapse
    G2 = aggregate_shipments(G)
    assert G2 is G
    assert any(d.get("type") == "shipment" for _, d in G2.nodes(data=True))


def test_aggregate_shipments_collapses_above_threshold():
    n = AGGREGATE_THRESHOLD + 3  # 63 shipments
    G2 = aggregate_shipments(_fan_out_graph(n))
    assert not any(d.get("type") == "shipment" for _, d in G2.nodes(data=True))
    # weights count the collapsed shipments per retailer
    assert G2["FG-1"]["RET-A"]["weight"] == sum(1 for i in range(n) if i % 3)
    assert G2["FG-1"]["RET-B"]["weight"] == sum(1 for i in range(n) if not i % 3)
    assert G2["FG-1"]["RET-A"]["aggregated"] is True
    # original graph untouched (copy semantics)
    assert n + 3 == len(_fan_out_graph(n).nodes)


def test_scope_row_to_panel_maps_and_rounds():
    row = {
        "lots_affected": 4, "skus_affected": 2,
        "cases_in_channel": 120, "cases_sold_through": 80,
        "direct_cost_low": 1080.456, "direct_cost_high": 1680.0,
        "notification_list": ["Walmart", "Costco"],
    }
    panel = scope_row_to_panel(row)
    assert panel["lots_affected"] == 4
    assert panel["cases_in_channel"] == 120
    assert panel["cost_low"] == 1080.46  # rounded to 2 places
    assert panel["cost_high"] == 1680.0
    assert panel["notification_list"] == ["Walmart", "Costco"]


def test_scope_row_to_panel_null_safe():
    panel = scope_row_to_panel({})
    assert panel == _empty_scope()


def test_graph_to_api_format_shape():
    G = build_graph(CHAIN_ROWS)
    out = graph_to_api_format(G, "ING-001", _empty_scope())
    assert out["lot_id"] == "ING-001"
    assert len(out["nodes"]) == 5
    assert len(out["edges"]) == 4
    assert {"source": "ING-001", "target": "B-100"} in out["edges"]
    node_keys = set(out["nodes"][0].keys())
    assert node_keys == {"id", "type", "label", "depth"}


def test_empty_scope_shape():
    s = _empty_scope()
    assert s["lots_affected"] == 0
    assert s["cost_low"] == 0.0
    assert s["notification_list"] == []
