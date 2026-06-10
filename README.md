# Recall Blast Radius

**Live:** https://recall.lailarallc.com

A food recall is a graph problem. Pick an ingredient lot, a production run, or a packaging lot and watch the contamination propagate forward through the genealogy: ingredient → batch → finished-goods lot → case → shipment → DC → retailer → store. The scope panel updates live: units still in channel, estimated sold-through, disposal and logistics cost, and the notification list. At most $25M brands, the honest answer to "what's our blast radius?" is "give us three days." This is the three-hours version.

## Cinderhaven context

Built on the Cinderhaven synthetic dataset — a ~$25M specialty food brand, 50 SKUs across 5 product lines and 6 contracted retailers. Data is synthetic; methodology and deliverables are real.

Extends the platform with a new lot/batch genealogy dimension — the first new dimension since Dimension & Weight. Genealogy seed is isolated (seed=TBD), registered in `CINDERHAVEN_CANONICAL.md`, with drift-guard coverage.

## What it finds

Three preset scenarios show how blast radius scales non-linearly with where in the BOM the contamination sits:

- **Scenario A — Single ingredient lot:** one input, one product line, bounded impact
- **Scenario B — Shared ingredient across lines:** one chili lot, 14 SKUs, 3 product lines — the gut-punch case
- **Scenario C — Packaging lot:** spans everything sharing a label run, irrespective of ingredient

Each scenario produces: units in channel, estimated sold-through, direct cost range (disposal + freight + retailer handling + admin), and the trading-partner notification list.

FSMA 204 KDE/CTE mapping table shows which Key Data Elements at which Critical Tracking Events the Cinderhaven data captures and where the gaps are.

## Stack

- Python 3.12 — NetworkX (graph construction, traversal, scope computation)
- FastAPI — traversal API
- Postgres — lot genealogy tables, recursive CTE traversal
- dbt — genealogy models and platform extension
- D3 v7 (force / hierarchical layout) — blast-radius visualization
- Dagster — asset integration with platform

## Data contract

**Canonical baseline:** 50 SKUs · 5 product lines (AS·PS·SC·DG·SB) · 6 retailers
(Walmart·Costco·Whole Foods·Sprouts·Kroger·Regional Group) · 10 channels
(6 retail + UNFI·KeHE·DPI + DTC)

Extends canonical with: ingredient lots · production batches · finished-goods lots · case-level allocation. Genealogy seed isolated from platform seed per Cinderhaven canonical governance.

## Run

```bash
# Prerequisites: Docker (Postgres), Python 3.12, Node 20

# 1. Start Postgres
docker compose up -d db

# 2. Install Python deps
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt

# 3. Load genealogy data
dbt deps && dbt seed && dbt run

# 4. Start API
uvicorn api.main:app --reload

# 5. Serve frontend (separate terminal)
cd frontend && npm install && npm run dev
```

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
