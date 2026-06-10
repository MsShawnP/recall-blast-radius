from fastapi import APIRouter, HTTPException
from api.models.genealogy import TraceRequest, TraceResult, ScenarioGraph

router = APIRouter()


@router.post("/trace", response_model=TraceResult)
def trace_lot(request: TraceRequest):
    """
    Trace forward or backward from a given lot_id.
    Returns graph nodes/edges and scope summary.
    """
    # TODO: query genealogy mart, build NetworkX graph, compute scope
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/scenarios")
def get_scenarios() -> list[ScenarioGraph]:
    """Return the three preset blast-radius scenarios."""
    # TODO: load pre-computed scenario graphs
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/lots")
def list_lots(q: str = ""):
    """Search available lots for the lot picker."""
    # TODO: query lot index from DB
    raise HTTPException(status_code=501, detail="Not implemented")
