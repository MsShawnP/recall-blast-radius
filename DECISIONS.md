# DECISIONS — recall-blast-radius

---

## D-014 — lailara-website repo location for portfolio work

**Decision:** The lailara-website Next.js source is at `C:\Users\mssha\projects\reference\lailara-website\site`. Use `gh repo list MsShawnP` to locate any repo, not filesystem search.

**Date:** 2026-06-11

**Why:** Repo lives in `reference/`, not `active/` or `published/`. Filesystem searches iterated through all three before finding it.

**Scope:** Any session that touches the main website (portfolio cards, pillar pages, nav, global layout).

**Do not:** Search with `find` or `glob` for the website source — use `gh repo list` then check `reference/lailara-website/site`.

---

## D-001 — FSMA 204 compliance date to cite in the piece
**Decision:** July 20, 2028  
**Date:** 2026-06-10  
**Rationale:** Original date (January 20, 2026) was extended by FDA via proposed rule FR Doc. 2025-14967 (August 7, 2025). Congress independently locked in July 20, 2028 as the non-enforcement date via the Continuing Appropriations Act of 2026 (November 2025). Operationally binding. **Primary source:** federalregister.gov/documents/2025/08/07/2025-14967

---

## D-002 — Cinderhaven SKU FTL coverage
**Decision:** Hot sauces and dry spice blends are NOT on the FDA Food Traceability List. Do not describe them as FSMA 204-covered finished goods.  
**Credibility marker to use:** Acknowledge the upstream nuance — if FTL-listed raw ingredients (fresh peppers, leafy greens) enter the co-packer's supply chain, partial traceability obligations attach to *that upstream step*, not to the finished shelf-stable SKU. This is the detail that signals someone who read the rule.  
**Date:** 2026-06-10

---

## D-003 — Retailer mandate framing
**Decision:** Cite Walmart (August 1, 2025, all food suppliers) and Kroger (GS1-standard, all food products entering facilities) as already past their internal deadlines — independent of the FDA extension. The regulatory clock is largely theater; the channel pressure is live.  
**Source quality:** Walmart — primary (Walmart food safety supplier portal). Kroger — secondary (Food Safety Magazine). Do not cite a specific Kroger date without better sourcing.  
**Date:** 2026-06-10

---

## D-004 — Recall cost figure and attribution
**Decision:** Use "$10M+ in direct costs" framed as a conservative floor. Correct attribution: 2010 Deloitte Consulting study commissioned by GMA and FMI (54 companies, $481B combined sales). Do NOT attribute to the GMA 2011 whitepaper — that document contains no $10M average; the attribution in secondary literature is a misattribution.  
**Qualifier to include:** "2010 Deloitte/GMA/FMI; Consumer Brands Association data suggests >50% of companies now exceed this, making it a floor."  
**Date:** 2026-06-10

---

## D-005 — Genealogy seed number
**Decision:** seed=400  
**Rationale:** Existing seeds — 42 (main platform), 200 (distressed scenario), 300 (defect profile). Next available. Must be registered in CINDERHAVEN_CANONICAL.md in cinderhaven-data-platform.  
**Date:** 2026-06-10

---

## D-006 — Trace direction in v1
**Decision:** Trace-forward only (ingredient lot → … → stores/retailers)  
**Rationale:** Trace-back (ingredient sourcing upstream from suppliers) adds co-packer supplier relationship complexity with no narrative payoff in the recall scenario. All three preset scenarios run forward. Trace-back is a natural v2 addition.  
**Date:** 2026-06-10

---

## D-007 — Preset scenarios vs. free lot picker
**Decision:** Both. Three preset scenarios for the narrative arc; free lot picker for any lot_id in the data.  
**Rationale:** The "data integrity work" concern in the brief is resolved by the seed being fully consistent — if every lot has valid genealogy, any lot_id is queryable. Presets are hardcoded for the story; the picker lets a reader explore.  
**Date:** 2026-06-10

---

## D-009 — Cite the Continuing Appropriations Act as primary FSMA 204 date authority
**Decision:** When citing the July 20, 2028 FSMA 204 date, the Continuing Appropriations Act of 2026 (November 2025) is the load-bearing citation — not FR Doc. 2025-14967 alone.  
**Why:** FR Doc. 2025-14967 is a *proposed* rule, not a final rule. A food-industry reader who notices the "proposed" status could dismiss the piece's regulatory framing. Congress's appropriations act independently mandates the same non-enforcement date and is not subject to the proposed/final caveat.  
**Scope:** Any page, copy, or client deliverable citing the FSMA 204 compliance date.  
**Do not:** Cite FR Doc. 2025-14967 as the sole authority. Always pair it with the Continuing Appropriations Act of 2026, or lead with the Congressional citation.  
**Date:** 2026-06-10

---

## D-010 — Commit scenario cache to the repo

**Decision:** `pipeline/cache/scenario_graphs.json` is committed to git alongside the source code.

**Date:** 2026-06-10

**Why:** The `/scenarios` endpoint reads from this file at serve time. Without it in the repo, deploying the API requires running `build_cache.py` against the live database as a post-deploy step — adding a Fly proxy dependency to the deploy pipeline. Committing the cache means the API serves scenarios on boot, with no DB required for that endpoint.

**Scope:** This repo only. The cache is generated data, but the deploy-time tradeoff favors committing it.

**Do not:** Commit the cache after a seed change without verifying the scenario graphs still match the narrative copy (case counts, retailer lists, cost figures are cited in index.html).

---

## D-011 — Use `python -m uvicorn` not bare `uvicorn` on this machine

**Decision:** All launch configs and scripts that start uvicorn use `python -m uvicorn`, not `uvicorn` as a standalone executable.

**Date:** 2026-06-10

**Why:** On Windows Store Python, uvicorn's script entry point is not on the system PATH. `uvicorn` as a command produces `ENOENT`; `python -m uvicorn` works because Python itself is on PATH.

**Scope:** `.claude/launch.json`, any Makefile or run script added to this repo, deployment documentation.

**Do not:** Use bare `uvicorn` as a command in any config file in this project.

---

## D-012 — Use preview_snapshot over preview_screenshot for page verification

**Decision:** `preview_snapshot` (accessibility tree) is the primary tool for verifying page content in this project. `preview_screenshot` is unreliable with D3 SVG pages.

**Date:** 2026-06-10

**Why:** D3 force simulations and/or the headless browser renderer cause `preview_screenshot` to time out consistently (30s). `preview_snapshot` returns the full DOM text tree instantly and is sufficient to verify labels, structure, and data values. Use `preview_eval` for computed values or JS state.

**Scope:** All frontend verification in this project during development.

---

## D-013 — Use Cloudflare REST API (not wrangler) for Pages custom domains

**Decision:** Add custom domains to Cloudflare Pages projects via the REST API, not wrangler CLI. Create the CNAME DNS record explicitly as a second call.

**Date:** 2026-06-11

**Why:** `wrangler pages domain add` does not exist in wrangler v4. The REST API works reliably with `CLOUDFLARE_API_TOKEN` already in the environment.

**Scope:** All Lailara Cloudflare Pages projects needing a custom subdomain.

**Do not:** Attempt `wrangler pages domain *` — the subcommand doesn't exist. Also: CNAME is not auto-provisioned by the Pages domain-add API call even on same-account zones — always create it explicitly via `POST /zones/{zone_id}/dns_records` with `"proxied": true`.

**Endpoints:**
- Add domain: `POST /accounts/{account_id}/pages/projects/{name}/domains` `{"name":"sub.lailarallc.com"}`
- Add CNAME: `POST /zones/{zone_id}/dns_records` `{"type":"CNAME","name":"sub","content":"{name}.pages.dev","proxied":true,"ttl":1}`

---

## D-008 — Genealogy schema placement
**Decision:** Standalone Postgres in this repo (docker-compose). Includes stub platform tables (product_master, retailers, shipments) seeded from canonical values, plus new `genealogy` schema tables.  
**Rationale:** Portfolio piece must run standalone without a live connection to cinderhaven-data-platform on Fly.io. SKU IDs and retailer IDs are canonical-conformant (50 SKUs, 6 retailers) so downstream reconciliation is possible if integrated later.  
**Date:** 2026-06-10
