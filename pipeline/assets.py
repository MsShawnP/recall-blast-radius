import os
import psycopg2
from dagster import asset, AssetExecutionContext
from pipeline.generate_genealogy import generate_all

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/recall_blast_radius")


def _get_conn():
    return psycopg2.connect(DATABASE_URL)


@asset
def genealogy_seed(context: AssetExecutionContext):
    """Load genealogy seed data (seed=400) into Postgres."""
    data = generate_all()
    conn = _get_conn()
    cur  = conn.cursor()

    # Platform stubs
    for row in data["retailers"]:
        cur.execute("""
            INSERT INTO raw.retailers (retailer_id, retailer_name, store_doors)
            VALUES (%(retailer_id)s, %(retailer_name)s, %(store_doors)s)
            ON CONFLICT (retailer_id) DO NOTHING
        """, row)

    for row in data["product_master"]:
        cur.execute("""
            INSERT INTO raw.product_master (sku_id, sku_name, product_line, cases_per_pallet)
            VALUES (%(sku_id)s, %(sku_name)s, %(product_line)s, %(cases_per_pallet)s)
            ON CONFLICT (sku_id) DO NOTHING
        """, row)

    for row in data["shipments"]:
        cur.execute("""
            INSERT INTO raw.shipments (shipment_id, order_id, retailer_id, ship_date, cases_shipped)
            VALUES (%(shipment_id)s, %(order_id)s, %(retailer_id)s, %(ship_date)s, %(cases_shipped)s)
            ON CONFLICT (shipment_id) DO NOTHING
        """, row)

    # Genealogy tables
    for row in data["co_packers"]:
        cur.execute("""
            INSERT INTO genealogy.co_packers (co_packer_id, name, lot_code_format, primary_lines)
            VALUES (%(co_packer_id)s, %(name)s, %(lot_code_format)s, %(primary_lines)s)
            ON CONFLICT (co_packer_id) DO NOTHING
        """, row)

    for row in data["ingredients"]:
        cur.execute("""
            INSERT INTO genealogy.ingredients (ingredient_id, name, category, is_ftl_upstream, unit)
            VALUES (%(ingredient_id)s, %(name)s, %(category)s, %(is_ftl_upstream)s, %(unit)s)
            ON CONFLICT (ingredient_id) DO NOTHING
        """, row)

    for row in data["ingredient_lots"]:
        cur.execute("""
            INSERT INTO genealogy.ingredient_lots
              (ingredient_lot_id, ingredient_id, co_packer_id, supplier_name,
               supplier_lot_code, co_packer_lot_code, quantity_lbs,
               received_date, best_by_date, status)
            VALUES (%(ingredient_lot_id)s, %(ingredient_id)s, %(co_packer_id)s,
                    %(supplier_name)s, %(supplier_lot_code)s, %(co_packer_lot_code)s,
                    %(quantity_lbs)s, %(received_date)s, %(best_by_date)s, %(status)s)
            ON CONFLICT (ingredient_lot_id) DO NOTHING
        """, row)

    for row in data["production_batches"]:
        cur.execute("""
            INSERT INTO genealogy.production_batches
              (batch_id, sku_id, co_packer_id, production_date,
               batch_quantity_cases, co_packer_batch_code, status)
            VALUES (%(batch_id)s, %(sku_id)s, %(co_packer_id)s, %(production_date)s,
                    %(batch_quantity_cases)s, %(co_packer_batch_code)s, %(status)s)
            ON CONFLICT (batch_id) DO NOTHING
        """, row)

    for row in data["batch_ingredient_map"]:
        cur.execute("""
            INSERT INTO genealogy.batch_ingredient_map
              (batch_id, ingredient_lot_id, quantity_used_lbs)
            VALUES (%(batch_id)s, %(ingredient_lot_id)s, %(quantity_used_lbs)s)
            ON CONFLICT (batch_id, ingredient_lot_id) DO NOTHING
        """, row)

    for row in data["fg_lots"]:
        cur.execute("""
            INSERT INTO genealogy.fg_lots
              (fg_lot_id, batch_id, sku_id, internal_lot_code, co_packer_lot_code,
               quantity_cases, production_date, best_by_date, status)
            VALUES (%(fg_lot_id)s, %(batch_id)s, %(sku_id)s, %(internal_lot_code)s,
                    %(co_packer_lot_code)s, %(quantity_cases)s, %(production_date)s,
                    %(best_by_date)s, %(status)s)
            ON CONFLICT (fg_lot_id) DO NOTHING
        """, row)

    for row in data["packaging_lots"]:
        cur.execute("""
            INSERT INTO genealogy.packaging_lots
              (packaging_lot_id, packaging_type, supplier_name, lot_code,
               quantity_units, received_date)
            VALUES (%(packaging_lot_id)s, %(packaging_type)s, %(supplier_name)s,
                    %(lot_code)s, %(quantity_units)s, %(received_date)s)
            ON CONFLICT (packaging_lot_id) DO NOTHING
        """, row)

    for row in data["batch_packaging_map"]:
        cur.execute("""
            INSERT INTO genealogy.batch_packaging_map (batch_id, packaging_lot_id)
            VALUES (%(batch_id)s, %(packaging_lot_id)s)
            ON CONFLICT (batch_id, packaging_lot_id) DO NOTHING
        """, row)

    for row in data["shipment_lot_map"]:
        cur.execute("""
            INSERT INTO genealogy.shipment_lot_map
              (shipment_id, fg_lot_id, cases_shipped, cases_in_channel, cases_sold_through)
            VALUES (%(shipment_id)s, %(fg_lot_id)s, %(cases_shipped)s,
                    %(cases_in_channel)s, %(cases_sold_through)s)
            ON CONFLICT (shipment_id, fg_lot_id) DO NOTHING
        """, row)

    for row in data["scenarios"]:
        cur.execute("""
            INSERT INTO genealogy.scenarios
              (scenario_id, title, description, root_node_type, root_node_id)
            VALUES (%(scenario_id)s, %(title)s, %(description)s,
                    %(root_node_type)s, %(root_node_id)s)
            ON CONFLICT (scenario_id) DO UPDATE SET
              title          = EXCLUDED.title,
              description    = EXCLUDED.description,
              root_node_type = EXCLUDED.root_node_type,
              root_node_id   = EXCLUDED.root_node_id
        """, row)

    conn.commit()
    cur.close()
    conn.close()

    context.log.info(f"Loaded genealogy seed: "
                     f"{len(data['ingredient_lots'])} ingredient lots, "
                     f"{len(data['production_batches'])} batches, "
                     f"{len(data['fg_lots'])} FG lots, "
                     f"{len(data['shipment_lot_map'])} shipment links")


@asset(deps=[genealogy_seed])
def genealogy_graph(context: AssetExecutionContext):
    """Build NetworkX graph from genealogy mart tables (post-dbt run)."""
    import networkx as nx
    import json

    conn = _get_conn()
    cur  = conn.cursor()

    cur.execute("""
        SELECT root_lot_id, node_type, node_id, label, depth
        FROM genealogy.fct_blast_radius
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    G = nx.DiGraph()
    edges_seen = set()

    for root_lot_id, node_type, node_id, label, depth in rows:
        G.add_node(node_id, type=node_type, label=label, depth=depth)

    # Edges are implicit in the path progression — add via depth adjacency
    # (a proper implementation would store parent_id in fct_blast_radius)
    context.log.info(f"Graph: {G.number_of_nodes()} nodes")


@asset(deps=[genealogy_graph])
def scenario_graphs(context: AssetExecutionContext):
    """Pre-compute and cache the three preset blast-radius scenario responses."""
    # Each scenario calls the /trace endpoint logic against the scenario root_node_id.
    # Output is stored as JSON for fast API serving.
    pass
