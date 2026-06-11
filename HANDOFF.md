# HANDOFF — recall-blast-radius

## 2026-06-10 (Phase 4 complete)

**Started from:** Phases 0-3 done. Phase 4 (D3 visualization) was next.

**Did:** Complete Phase 4 frontend implementation:
- `frontend/src/graph.js` — full rewrite: depth-based Y force layering (ingredient→batch→fg_lot→shipment→retailer top-to-bottom), arrow-head directed edges (pre-shortened line endpoints), node sizing by type (ingredient/packaging 14px, retailer 12px, batch/fg_lot 10px, shipment 7px), click-to-pin with 200ms D3 opacity transition + dark callout card, node type legend
- `frontend/src/app.js` — full rewrite: scenario cache (single fetch), renderScenarioMeta (title + description below switcher), full scope panel (cases_in_channel, cases_sold_through + %, lots, SKUs, cost range, notification_list), `.graph-error` state for API-down
- `frontend/src/styles.css` — expanded (external pass added hook/loading/error classes, sticky scope panel, overflow:hidden on graph container)

**State:** Phase 4 complete and verified. All 3 scenarios render against live API (Fly proxy + uvicorn + `pipeline/cache/scenario_graphs.json`). Scenario A: 9 nodes, 121 cases. Scenario B: 53 nodes, 5,785 cases, 6 retailers to notify. Scenario C: 443 nodes (aggregated), 54,576 cases, $491K–$764K cost. Scope panel, legend, click-to-pin all working.

**Known data issue:** `cases_sold_through` > `cases_in_channel` in `fct_blast_radius_scope` estimate logic — display clamped to 100%; underlying dbt model bug to fix separately.

**To start dev:** `flyctl proxy 5432 -a cinderhaven-db` → `python -m uvicorn api.main:app --reload` → `python -m http.server 3000 --directory frontend`

**Next:** Phase 6 — Fly.io FastAPI deploy + Cloudflare Pages frontend + recall.lailarallc.com subdomain.

---

## 2026-06-10 (Phase 5 complete)

**Did:** Full narrative and evidence layer — Scenario B gut-punch copy (47× blast radius from one shared lot), margin math ($52K–$81K retrieval vs $10M+ industry average vs ~$2.75M Cinderhaven EBITDA), FSMA 204 KDE/CTE mapping table (Receiving/Transformation/Shipping, 17 KDEs, 2 "Planned" gaps: BOL reference docs), 10-question traceability readiness checklist. All verified in preview.

**State:** Phases 0–5 complete. Frontend is fully functional (API + D3 graph + narrative). Ready for deployment.

**To start dev:** `flyctl proxy 5432 -a cinderhaven-db` → `python -m uvicorn api.main:app --reload` → `python -m http.server 3000 --directory frontend`

---

## 2026-06-10 18:30

**Started from:** Brand new project. Only `brief_recall_blast_radius.md` existed.

**Did:** Full scaffold + Phase 0 deep-research (96-agent, 14 confirmed claims) + Phase 1 genealogy schema — DDL, recursive CTE, seed generator (seed=400), dbt staging + mart models, dbt sources.yml tests, Dagster loader asset.

**State:** All Phase 1 files written, nothing run. Two known bugs: O(n²) BOM lookup in generate_genealogy.py; missing parent_id in fct_blast_radius. Not a git repo yet.

**Next:** Fix O(n²) BOM lookup + add parent_id → run end-to-end (docker compose → DDL → generate_genealogy.py → dbt run && dbt test) → register seed=400 in CINDERHAVEN_CANONICAL.md → then Phase 2 (FastAPI /trace endpoint).

---

**Session:** 2026-06-10 (Phase 0 research + Phase 1 schema)
**Phase:** 1 — Genealogy data model (mostly done; 2 tasks remain)
**Status:** Schema complete. Not yet run end-to-end.

---

## What was done this session

### Phase 0 research (complete)
- FSMA 204 date confirmed: **July 20, 2028** (FR Doc. 2025-14967 + Continuing Appropriations Act of 2026)
- Cinderhaven SKUs NOT on FTL (hot sauce / spice blends are shelf-stable); upstream nuance documented
- Walmart: all-food mandate, Aug 1 2025 (past); Kroger: all-food GS1 mandate (past)
- Recall cost: $10M+ (2010 Deloitte/GMA/FMI) — NOT the GMA 2011 whitepaper (common misattribution)
- All findings in DECISIONS.md (D-001 through D-008)

### Phase 1 data model (mostly complete)
Written but NOT run:
- `data/schema/genealogy_ddl.sql` — full DDL: co_packers, ingredients, ingredient_lots, production_batches, batch_ingredient_map, fg_lots, packaging_lots, batch_packaging_map, shipment_lot_map, scenarios + indexes
- `data/schema/trace_forward.sql` — recursive CTE (ingredient_lot → batch → fg_lot → shipment → retailer)
- `pipeline/generate_genealogy.py` — seed generator (seed=400); produces ~1,200 ingredient lots, ~600 batches, ~600 FG lots, ~2,400 shipment links, 3 preset scenarios
- `data/models/staging/` — stg_ingredient_lots, stg_production_batches, stg_fg_lots
- `data/models/genealogy/` — fct_blast_radius (recursive CTE mart), fct_blast_radius_scope (cost model)
- `data/models/sources.yml` — all sources with full dbt test coverage
- `pipeline/assets.py` — Dagster genealogy_seed asset (full Postgres loader)

## What doesn't work yet

End-to-end not run. Likely issues to find:
1. `generate_genealogy.py` BOM loop has a list comprehension lookup that's O(n²) — should be refactored to a dict lookup before running on full dataset
2. `fct_blast_radius` recursive CTE in dbt will be slow without pg_recursion depth guard; add `MAXRECURSION` config or depth limit
3. `dbt_project.yml` needs sources.yml location reference (`source-paths` or model-paths covers it)
4. The `genealogy_graph` Dagster asset needs parent_id stored in fct_blast_radius to build proper NetworkX edges

## What's next

**Immediate (finish Phase 1):**
1. Fix the O(n²) BOM lookup in generate_genealogy.py (pre-index ing_lot_pool by date)
2. Run: `docker compose up -d db && python pipeline/generate_genealogy.py` to verify counts
3. Run: `dbt run && dbt test` to verify models and tests pass
4. Register seed=400 in cinderhaven-data-platform/CINDERHAVEN_CANONICAL.md

**Then Phase 2 (graph construction):**
- Add parent_id to fct_blast_radius for NetworkX edge building
- Implement the NetworkX graph in genealogy_graph asset
- Wire up the /trace FastAPI endpoint against fct_blast_radius

## Key files

| File | Purpose |
|------|---------|
| `DECISIONS.md` | All research findings (D-001 to D-008) — cite these in the piece |
| `data/schema/genealogy_ddl.sql` | DDL — run this first against fresh Postgres |
| `pipeline/generate_genealogy.py` | Seed generator (seed=400) |
| `data/schema/trace_forward.sql` | The recursive CTE — the core query |
| `data/models/genealogy/fct_blast_radius.sql` | dbt-ified version of above |
| `data/models/genealogy/fct_blast_radius_scope.sql` | Scope panel data (cost model) |
| `pipeline/assets.py` | Dagster asset: genealogy_seed loads everything |

## Cost model (in fct_blast_radius_scope)
Direct cost per in-channel case: $9–$14 (disposal $4 + freight $1.50 + retailer fees $2.50 + admin $1)
This is the number that feeds the margin math in the piece.
