"""
Graph construction from the genealogy mart.

Builds NetworkX DiGraphs from fct_blast_radius rows and serializes them
to the TraceResult API format. Handles both ingredient-lot roots (Scenarios A/B)
and packaging-lot roots (Scenario C) which require a separate DB traversal.
"""

import networkx as nx


# Collapse shipment nodes into direct fg_lot→retailer edges when the graph
# exceeds this threshold — keeps D3 layouts readable for Scenario B.
AGGREGATE_THRESHOLD = 60


def build_graph(rows: list[tuple]) -> nx.DiGraph:
    """
    Build a DiGraph from fct_blast_radius rows.
    rows: (root_lot_id, node_type, node_id, label, depth, parent_id)
    """
    G = nx.DiGraph()
    for root_lot_id, node_type, node_id, label, depth, parent_id in rows:
        G.add_node(node_id, type=node_type, label=str(label), depth=depth,
                   root_lot_id=root_lot_id)
        if parent_id:
            G.add_edge(parent_id, node_id)
    return G


def subgraph_for_root(G: nx.DiGraph, root_lot_id: str) -> nx.DiGraph:
    """Extract the sub-graph for one root ingredient lot."""
    if root_lot_id not in G:
        return nx.DiGraph()
    reachable = nx.descendants(G, root_lot_id) | {root_lot_id}
    return G.subgraph(reachable).copy()


def aggregate_shipments(G: nx.DiGraph) -> nx.DiGraph:
    """
    Collapse shipment nodes into direct fg_lot→retailer edges when the graph
    is large. Adds a `weight` attribute counting the collapsed shipments.
    Only applied when shipment node count exceeds AGGREGATE_THRESHOLD.
    """
    shipment_nodes = [n for n, d in G.nodes(data=True)
                      if d.get("type") == "shipment"]
    if len(shipment_nodes) <= AGGREGATE_THRESHOLD:
        return G

    G2 = G.copy()
    for ship_id in shipment_nodes:
        fg_parents = list(G2.predecessors(ship_id))
        ret_children = list(G2.successors(ship_id))
        for fg_id in fg_parents:
            for ret_id in ret_children:
                if G2.has_edge(fg_id, ret_id):
                    G2[fg_id][ret_id]["weight"] += 1
                else:
                    G2.add_edge(fg_id, ret_id, weight=1, aggregated=True)
        G2.remove_node(ship_id)
    return G2


def packaging_lot_rows(conn, packaging_lot_id: str) -> list[tuple]:
    """
    Traverse batch_packaging_map → fg_lots → shipments → retailers for a
    packaging lot root, returning rows in the same shape as fct_blast_radius.
    """
    cur = conn.cursor()
    cur.execute("""
        with

        batch_level as (
            select
                %(root)s            as root_lot_id,
                'batch'             as node_type,
                b.batch_id          as node_id,
                b.co_packer_batch_code as label,
                1                   as depth,
                %(root)s            as parent_id
            from genealogy.batch_packaging_map bpm
            join genealogy.production_batches b using (batch_id)
            where bpm.packaging_lot_id = %(root)s
        ),

        fg_level as (
            select
                %(root)s            as root_lot_id,
                'fg_lot'            as node_type,
                fl.fg_lot_id        as node_id,
                fl.internal_lot_code as label,
                2                   as depth,
                b.node_id           as parent_id
            from batch_level b
            join genealogy.fg_lots fl on fl.batch_id = b.node_id
        ),

        shipment_level as (
            select
                %(root)s            as root_lot_id,
                'shipment'          as node_type,
                slm.shipment_id     as node_id,
                s.ship_date::text   as label,
                3                   as depth,
                f.node_id           as parent_id
            from fg_level f
            join genealogy.shipment_lot_map slm on slm.fg_lot_id = f.node_id
            join raw.shipments s on s.shipment_id = slm.shipment_id
        ),

        retailer_level as (
            select
                %(root)s            as root_lot_id,
                'retailer'          as node_type,
                r.retailer_id       as node_id,
                r.retailer_name     as label,
                4                   as depth,
                sh.node_id          as parent_id
            from shipment_level sh
            join raw.shipments s on s.shipment_id = sh.node_id
            join raw.retailers r on r.retailer_id = s.retailer_id
        )

        select root_lot_id, node_type, node_id, label, depth, parent_id
        from batch_level
        union all
        select root_lot_id, node_type, node_id, label, depth, parent_id
        from fg_level
        union all
        select root_lot_id, node_type, node_id, label, depth, parent_id
        from shipment_level
        union all
        select root_lot_id, node_type, node_id, label, depth, parent_id
        from retailer_level
    """, {"root": packaging_lot_id})
    rows = cur.fetchall()
    cur.close()

    # Prepend the packaging lot root node itself
    root_row = (packaging_lot_id, "packaging_lot", packaging_lot_id,
                packaging_lot_id, 0, None)
    return [root_row] + rows


def packaging_lot_scope(conn, packaging_lot_id: str, rows: list[tuple]) -> dict:
    """Compute scope for a packaging lot from its traversal rows."""
    fg_lot_ids = [r[2] for r in rows if r[1] == "fg_lot"]
    shipment_ids = [r[2] for r in rows if r[1] == "shipment"]
    retailer_ids = list({r[2] for r in rows if r[1] == "retailer"})

    if not fg_lot_ids:
        return _empty_scope()

    cur = conn.cursor()

    # SKUs and cases from fg_lots
    cur.execute("""
        select count(distinct sku_id) as skus_affected,
               count(*) as fg_lots_affected,
               sum(quantity_cases) as total_cases
        from genealogy.fg_lots
        where fg_lot_id = any(%s)
    """, (fg_lot_ids,))
    fg_row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

    # Cases in channel / sold through
    cur.execute("""
        select coalesce(sum(cases_shipped), 0) as cases_shipped,
               coalesce(sum(cases_in_channel), 0) as cases_in_channel,
               coalesce(sum(cases_sold_through), 0) as cases_sold_through
        from genealogy.shipment_lot_map
        where shipment_id = any(%s)
    """, (shipment_ids,) if shipment_ids else ([],))
    ship_row = dict(zip([d[0] for d in cur.description], cur.fetchone()))

    # Retailer names
    cur.execute("""
        select array_agg(distinct retailer_name)
        from raw.retailers where retailer_id = any(%s)
    """, (retailer_ids,))
    notification_list = cur.fetchone()[0] or []
    cur.close()

    in_channel = int(ship_row["cases_in_channel"])
    return {
        "lots_affected":      int(fg_row["fg_lots_affected"] or 0),
        "skus_affected":      int(fg_row["skus_affected"] or 0),
        "cases_in_channel":   in_channel,
        "cases_sold_through": int(ship_row["cases_sold_through"] or 0),
        "cost_low":           round(in_channel * 9.0, 2),
        "cost_high":          round(in_channel * 14.0, 2),
        "notification_list":  sorted(notification_list),
    }


def scope_row_to_panel(row: dict) -> dict:
    in_channel = int(row.get("cases_in_channel") or 0)
    return {
        "lots_affected":      int(row.get("lots_affected") or 0),
        "skus_affected":      int(row.get("skus_affected") or 0),
        "cases_in_channel":   in_channel,
        "cases_sold_through": int(row.get("cases_sold_through") or 0),
        "cost_low":           round(float(row.get("direct_cost_low") or 0), 2),
        "cost_high":          round(float(row.get("direct_cost_high") or 0), 2),
        "notification_list":  row.get("notification_list") or [],
    }


def graph_to_api_format(G: nx.DiGraph, root_lot_id: str, scope: dict) -> dict:
    """Serialize a NetworkX graph to the TraceResult API shape."""
    nodes = [
        {"id": n, "type": d.get("type", "unknown"),
         "label": d.get("label", n), "depth": d.get("depth")}
        for n, d in G.nodes(data=True)
    ]
    edges = [{"source": s, "target": t} for s, t in G.edges()]
    return {"lot_id": root_lot_id, "nodes": nodes, "edges": edges, "scope": scope}


def _empty_scope() -> dict:
    return {"lots_affected": 0, "skus_affected": 0, "cases_in_channel": 0,
            "cases_sold_through": 0, "cost_low": 0.0, "cost_high": 0.0,
            "notification_list": []}
