"""
Standalone scenario cache builder — no Dagster required.
Produces pipeline/cache/scenario_graphs.json for the /scenarios API endpoint.

Usage:
    python pipeline/build_cache.py
"""

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

import psycopg2

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://recall_blast_radius_app:***REMOVED***@localhost:5432/recall_blast_radius",
)


def get_conn():
    p = urlparse(DATABASE_URL)
    return psycopg2.connect(
        host=p.hostname, port=p.port or 5432,
        dbname=p.path.lstrip("/"),
        user=p.username,
        password=unquote(p.password) if p.password else None,
    )


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from pipeline.graph import (
        _empty_scope, aggregate_shipments, build_graph,
        graph_to_api_format, packaging_lot_rows, packaging_lot_scope,
        scope_row_to_panel, subgraph_for_root,
    )

    print("Connecting...")
    conn = get_conn()
    cur = conn.cursor()

    print("Loading fct_blast_radius...")
    cur.execute(
        "SELECT root_lot_id, node_type, node_id, label, depth, parent_id "
        "FROM public.fct_blast_radius"
    )
    br_rows = cur.fetchall()
    print(f"  {len(br_rows)} rows")

    cur.execute("SELECT * FROM public.fct_blast_radius_scope")
    cols = [d[0] for d in cur.description]
    scope_by_root = {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}

    cur.execute(
        "SELECT scenario_id, title, description, root_node_type, root_node_id "
        "FROM genealogy.scenarios ORDER BY scenario_id"
    )
    scenarios = [
        {"id": r[0], "title": r[1], "description": r[2],
         "root_node_type": r[3], "root_node_id": r[4]}
        for r in cur.fetchall()
    ]
    cur.close()

    G = build_graph(br_rows)
    print(f"Full graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    scenario_responses = []
    for s in scenarios:
        root_id = s["root_node_id"]
        if s["root_node_type"] == "packaging_lot":
            pkg_rows = packaging_lot_rows(conn, root_id)
            sub_G = build_graph(pkg_rows)
            scope = packaging_lot_scope(conn, root_id, pkg_rows)
        else:
            sub_G = subgraph_for_root(G, root_id)
            scope = scope_row_to_panel(scope_by_root[root_id]) \
                    if root_id in scope_by_root else _empty_scope()

        sub_G = aggregate_shipments(sub_G)
        result = graph_to_api_format(sub_G, root_id, scope)
        scenario_responses.append({
            "id": s["id"], "title": s["title"],
            "description": s["description"], "result": result,
        })
        print(
            f"  Scenario {s['id']}: {sub_G.number_of_nodes()} nodes, "
            f"{sub_G.number_of_edges()} edges, "
            f"{scope['cases_in_channel']} cases in channel"
        )

    conn.close()

    cache_dir = Path(__file__).parent / "cache"
    cache_dir.mkdir(exist_ok=True)
    cache_path = cache_dir / "scenario_graphs.json"
    cache_path.write_text(json.dumps(scenario_responses, indent=2, default=str))
    print(f"Wrote {cache_path}")
