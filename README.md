# Recall Blast Radius

Answers "how big is our recall?" in seconds instead of days — an interactive lot-genealogy tracer for specialty food brands.

**Live:** https://recall.lailarallc.com

## What it does

A food recall is a graph problem. Pick an ingredient lot, a production run, or a packaging lot and watch the contamination propagate forward through the genealogy: ingredient → batch → finished-goods lot → case → shipment → DC → retailer → store. The scope panel updates live: units still in channel, estimated sold-through, disposal and logistics cost, and the trading-partner notification list.

Three preset scenarios show how blast radius scales non-linearly with where in the BOM the contamination sits:

- **Scenario A — Single ingredient lot:** one input, one product line, bounded impact
- **Scenario B — Shared ingredient across lines:** one chili lot, 14 SKUs, 3 product lines — the gut-punch case
- **Scenario C — Packaging lot:** spans everything sharing a label run, irrespective of ingredient

Each scenario produces: units in channel, estimated sold-through, direct cost range (disposal + freight + retailer handling + admin), and the notification list. An FSMA 204 KDE/CTE mapping table shows which Key Data Elements at which Critical Tracking Events the data captures and where the gaps are.

## Why it matters

At most $25M brands, the honest answer to "what's our blast radius?" is "give us three days" — while the FDA wants lot-level records within 24 hours and product keeps selling through. Scoping the recall in hours instead of days directly reduces units to dispose, retailers to notify unnecessarily, and administrative cost. The same genealogy backbone is what FSMA 204 traceability compliance requires.

Built on the Cinderhaven synthetic dataset — a ~$25M specialty food brand, 50 SKUs across 5 product lines and 6 contracted retailers. Data is synthetic; methodology and deliverables are real.

## Quick start

Prerequisites: Docker (for Postgres), Python 3.12+.

```bash
# 1. Start Postgres
docker compose up -d db

# 2. Install Python deps
python -m venv .venv && source .venv/bin/activate   # Windows: .venv/Scripts/activate
pip install -r requirements.txt

# 3. Load genealogy data (DDL + seeded rows, seed=400)
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/recall_blast_radius
python pipeline/seed.py

# 4. Build dbt models (fct_blast_radius, fct_blast_radius_scope)
cp data/profiles.yml.example data/profiles.yml
cd data && dbt run && cd ..

# 5. Pre-compute the scenario cache
python pipeline/build_cache.py

# 6. Start the API
uvicorn api.main:app --reload

# 7. Serve the frontend (static — no build step)
cd frontend && python -m http.server 3000
```

Run tests with `pytest`. Deploys to Fly.io via `fly.toml` (API container defined in `Dockerfile`).

## Tech stack

- **Python** — FastAPI + Uvicorn traversal API, NetworkX for graph construction and scope computation
- **Postgres 16** — lot genealogy tables, recursive-CTE forward trace (`data/schema/`)
- **dbt** — genealogy models layered on the platform (`data/models/`)
- **Dagster** — asset integration with the wider Cinderhaven platform (`pipeline/assets.py`); standalone scripts (`pipeline/seed.py`, `pipeline/build_cache.py`) run without a Dagster instance
- **D3 v7** — force-layout blast-radius visualization, vanilla JS frontend with no build step
- **Deploy** — Docker, Fly.io

## Project structure

```
api/        FastAPI app (routers/trace.py — /api/trace, /health)
pipeline/   Genealogy generator (seed=400), seed loader, scenario cache builder, Dagster assets
data/       dbt project: staging + genealogy models, DDL, recursive trace SQL
frontend/   Static site: index.html + D3 graph (src/graph.js, src/app.js)
tests/      pytest suite (graph logic + API)
```

## Data contract

**Canonical baseline:** 50 SKUs · 5 product lines (AS·PS·SC·DG·SB) · 6 retailers (Walmart·Costco·Whole Foods·Sprouts·Kroger·Regional Group) · 10 channels (6 retail + UNFI·KeHE·DPI + DTC)

Extends canonical with: ingredient lots · production batches · finished-goods lots · case-level allocation. Genealogy seed (seed=400) is isolated from platform streams per Cinderhaven canonical governance, registered in `CINDERHAVEN_CANONICAL.md` with drift-guard coverage.

## License

MIT

---

Built by [Lailara LLC](https://lailarallc.com) — data hygiene and analytics consulting for specialty food brands scaling into national retail.
