# PLAN — recall-blast-radius

**Tier:** Heavy (new product, Cinderhaven extension, regulatory domain)
**Status:** Phase 3 complete — Phase 4 next (D3 frontend)

---

## Current Focus

Phase 4 — D3 visualization (force/hierarchical graph, scope panel, scenario switcher).

---

## Phases

### Phase 0 — Research ✅ DONE (2026-06-10)
- [x] FSMA 204 date: **July 20, 2028** (FR Doc. 2025-14967 + Continuing Appropriations Act of 2026)
- [x] Retailer mandates: Walmart all-food Aug 1 2025 (past); Kroger GS1 all-food (past)
- [x] Recall cost: **$10M+** (2010 Deloitte/GMA/FMI, conservative floor)
- [x] FTL coverage: hot sauces + spice blends NOT covered; upstream fresh ingredient caveat is the credibility marker
- [x] Trace direction: **forward only** in v1
- [x] Gate checklist: TBD (not blocking build)
- [x] Lot picker: **preset scenarios + free picker**
- [x] Genealogy seed: **400** (42/200/300 taken)

### Phase 1 — Genealogy data model ✅ DONE (2026-06-10)
- [x] Design lot genealogy schema — `data/schema/genealogy_ddl.sql`
- [x] Lot-code format realism — 3 co-packer formats (julian_line, sequential_date, yearweek_seq)
- [x] Recursive CTE traversal — `data/schema/trace_forward.sql`
- [x] Seed data generator — `pipeline/generate_genealogy.py` (seed=400)
- [x] dbt staging models — stg_ingredient_lots, stg_production_batches, stg_fg_lots
- [x] dbt genealogy mart — fct_blast_radius, fct_blast_radius_scope
- [x] dbt: sources.yml with tests (not-null, unique, referential integrity, accepted_values)
- [x] Dagster: genealogy_seed asset (loads all tables) + genealogy_graph stub
- [x] Register seed=400 in CINDERHAVEN_CANONICAL.md — **TODO: do this in cinderhaven-data-platform**
- [x] Run end-to-end: docker compose up → generate_genealogy → dbt run → verify counts

### Phase 2 — Graph construction ✅ DONE (2026-06-10)
- [x] Python: build NetworkX graph from genealogy mart
- [x] Implement trace-forward traversal (lot → cases in channel)
- [x] Implement scope computation (units, sold-through estimate, cost model)
- [x] Generate three preset scenario graphs (A: single lot, B: shared ingredient, C: packaging lot)
- [x] Aggregation strategy for large graphs (collapse shipments → direct fg_lot→retailer edges >60 nodes)
- [ ] Node aggregation / collapsible levels for D3 — deferred to Phase 4 (frontend)

### Phase 3 — FastAPI traversal API ✅ DONE (2026-06-10)
- [x] POST /trace — given a lot_id and direction, return graph + scope
- [x] GET /scenarios — return preset scenario graphs
- [x] GET /lots — search/list available lots
- [x] Health endpoint
- [ ] Dockerfile for Fly.io — deferred to Phase 6

### Phase 4 — D3 visualization
- [ ] Force/hierarchical layout for blast-radius graph
- [ ] Click-to-pin detail cards (dark callout, Lailara design system)
- [ ] Scope panel: units, sold-through, cost range, notification list
- [ ] Three scenario switcher
- [ ] Node collapse/expand for large graphs
- [ ] Mobile layout

### Phase 5 — Narrative and content
- [ ] Part 1: hook copy ("It's 2pm Friday...")
- [ ] Part 2: scenario narrative (B is the gut-punch)
- [ ] Part 3: FSMA 204 KDE/CTE mapping table
- [ ] Traceability readiness checklist (page + PDF)
- [ ] Margin math copy (Scenario B cost vs. Cinderhaven net income)

### Phase 6 — Deployment
- [ ] Fly.io: FastAPI deploy
- [ ] Cloudflare Pages: frontend deploy
- [ ] recall.lailarallc.com subdomain
- [ ] Dagster asset integration

### Phase 7 — Portfolio integration
- [ ] /work engagement card: "Risk & Traceability"
- [ ] LinkedIn post: shared-ingredient scenario screen capture

---

## Open Questions

| Question | Status |
|----------|--------|
| Trace-back in v1? | Open |
| Gate the checklist PDF? | Open |
| Free lot picker vs. preset-only? | Open |
| Genealogy seed number | Open |
| Final title | Open — working: "The Blast Radius" |

---

## Out of Scope (v1)

- Allergen-labeling consistency analysis
- FDA inspection database mining
- Real supplier/ingredient pricing
- Recall insurance analysis
