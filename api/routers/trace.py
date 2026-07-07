import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from api.db import get_conn
from api.models.genealogy import LotSummary, ScenarioGraph, TraceRequest, TraceResult
from pipeline.graph import (
    _empty_scope,
    aggregate_shipments,
    build_graph,
    packaging_lot_rows,
    packaging_lot_scope,
    scope_row_to_panel,
    graph_to_api_format,
)

logger = logging.getLogger(__name__)

router = APIRouter()

SCENARIO_CACHE = Path(__file__).parent.parent.parent / "pipeline" / "cache" / "scenario_graphs.json"


@router.post("/trace", response_model=TraceResult)
def trace_lot(request: TraceRequest):
    """Trace forward from a lot_id. Returns graph nodes/edges and scope summary."""
    if request.direction == "backward":
        raise HTTPException(status_code=400, detail="Trace-back not implemented in v1")

    conn = get_conn()
    try:
        cur = conn.cursor()

        # Try ingredient lot first (fct_blast_radius is indexed on root_lot_id)
        cur.execute(
            "SELECT root_lot_id, node_type, node_id, label, depth, parent_id "
            "FROM public.fct_blast_radius WHERE root_lot_id = %s",
            (request.lot_id,),
        )
        rows = cur.fetchall()

        if rows:
            cur.execute(
                "SELECT * FROM public.fct_blast_radius_scope WHERE root_lot_id = %s",
                (request.lot_id,),
            )
            cols = [d[0] for d in cur.description]
            scope_row = cur.fetchone()
            scope = scope_row_to_panel(dict(zip(cols, scope_row))) if scope_row else _empty_scope()
            cur.close()

            G = aggregate_shipments(build_graph(rows))
            return graph_to_api_format(G, request.lot_id, scope)

        # Try packaging lot
        cur.execute(
            "SELECT 1 FROM genealogy.packaging_lots WHERE packaging_lot_id = %s",
            (request.lot_id,),
        )
        if cur.fetchone():
            cur.close()
            pkg_rows = packaging_lot_rows(conn, request.lot_id)
            scope = packaging_lot_scope(conn, request.lot_id, pkg_rows)
            G = aggregate_shipments(build_graph(pkg_rows))
            return graph_to_api_format(G, request.lot_id, scope)

        cur.close()
        raise HTTPException(status_code=404, detail=f"Lot '{request.lot_id}' not found")

    finally:
        conn.close()


@router.get("/scenarios", response_model=list[ScenarioGraph])
def get_scenarios():
    """Return the three preset blast-radius scenario graphs (pre-computed cache)."""
    if not SCENARIO_CACHE.exists():
        logger.error(
            "Scenario cache not built yet at %s — run the genealogy_graph "
            "Dagster asset to materialize it.",
            SCENARIO_CACHE,
        )
        raise HTTPException(
            status_code=503,
            detail="Scenario data is temporarily unavailable — please try again in a minute.",
        )
    return json.loads(SCENARIO_CACHE.read_text())


@router.get("/lots", response_model=list[LotSummary])
def list_lots(q: str = ""):
    """Search ingredient lots by lot ID or ingredient name. Returns up to 50 results."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if q:
            cur.execute(
                """
                SELECT il.ingredient_lot_id, i.name, il.received_date::text, il.status
                FROM genealogy.ingredient_lots il
                JOIN genealogy.ingredients i USING (ingredient_id)
                WHERE il.ingredient_lot_id ILIKE %s OR i.name ILIKE %s
                ORDER BY il.received_date DESC
                LIMIT 50
                """,
                (f"%{q}%", f"%{q}%"),
            )
        else:
            cur.execute(
                """
                SELECT il.ingredient_lot_id, i.name, il.received_date::text, il.status
                FROM genealogy.ingredient_lots il
                JOIN genealogy.ingredients i USING (ingredient_id)
                ORDER BY il.received_date DESC
                LIMIT 50
                """
