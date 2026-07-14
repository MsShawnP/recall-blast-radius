# Positioning Brief: Recall Blast Radius

**Status:** Shipped — live at [recall.lailarallc.com](https://recall.lailarallc.com)
**Updated:** July 13, 2026. Rewritten against the shipped tool. Supersedes the June 10 pre-build brief, whose Scenario B economics ($600K–$1.2M) were a guess made before the cost model existed. Every figure below traces to a repo artifact; the ledger at the end lists each one.
**Dataset disclosure:** Cinderhaven Provisions is synthetic — a fabricated ~$25M specialty food brand (50 SKUs, 5 product lines, 6 retailers, genealogy seed=400, registered in `CINDERHAVEN_CANONICAL.md`). Cinderhaven is not a client and its numbers are illustrative. The methodology, the data model, and the deliverables are real.

---

## The Pain

A retailer or the FDA calls: an ingredient lot is implicated. FDA wants lot-level records within 24 hours. At most $25M brands, the genealogy that answers "which of our lots used it, which SKUs, which retailers, how many cases are still out there" lives in three places that have never been joined — the co-packer's batch records, the 3PL's shipment logs, and the ERP. The honest internal answer is "give us three days," and product keeps selling through while the days pass.

FSMA 204 puts a date on this: traceability records at each Critical Tracking Event for foods on the Food Traceability List, compliance deadline July 20, 2028. Hot sauces and spice blends are not on the current FTL — but their fresh upstream ingredients can trigger requirements at the receiving CTE, and Walmart and Kroger are pushing KDE/CTE data expectations onto suppliers regardless of what FDA enforces first.

## What Shipped

An interactive trace-forward graph. Pick a contaminated input — ingredient lot, production batch, packaging lot — and watch it propagate through the genealogy: ingredient → batch → finished-goods lot → shipment → DC → retailer. A scope panel updates live: lots and SKUs affected, cases still in channel versus sold through, direct retrieval cost, and the trading-partner notification list. Around the graph: an FSMA 204 KDE/CTE mapping table (17 KDEs across Receiving, Transformation, and Shipping; two gaps, both BOL reference documents) and a ten-question traceability readiness checklist.

Three preset scenarios carry the argument.

## The Number That Carries the Piece: 47.8×

Scenario A is the recall brands imagine. One chili-flakes lot went into one production batch: 1 SKU, 121 cases in channel, three retailers to notify, $1,089–$1,694 to retrieve. A spreadsheet and a long afternoon handle it.

Scenario B is the same ingredient at the same brand, except the co-manufacturer drew from that lot across 23 production batches. The result: 23 finished-goods lots, 14 SKUs across two of Cinderhaven's five product lines, all six retailers on the notification list, 5,785 cases still in channel — 47.8 times Scenario A's in-channel exposure, from one shared ingredient lot. Nothing about the contamination changed. The BOM position did.

Scenario C rounds out the curve: a packaging lot — one label run — implicates 218 finished-goods lots and all 50 SKUs, 54,576 cases in channel, $491K–$764K to retrieve. The deeper the shared input sits in the bill of materials, the less linearly the radius scales.

## The Cost Framing, Stated Honestly

The tool prices Scenario B at $52K–$81K. That figure is total direct retrieval cost, and it is deliberately narrow: 5,785 in-channel cases × $9–$14 per case (disposal $4, freight $1.50, retailer handling fees $2.50, administration $1). It excludes sold-through units, lab testing, legal, PR, disposal of returned consumer units, lost shelf placement, and brand damage. It also assumes the recall is scoped to exactly the 23 affected lots — which is the entire premise of the tool.

Set that against the industry-average cost of a full recall: $10M+ (Deloitte/GMA/FMI, 2010 — a conservative floor, before attorney fees or brand damage). The two numbers are not in tension; the gap between them is the argument. $10M is what happens when a brand — usually a larger one — cannot prove which lots are clean and withdraws broadly, then pays for testing, legal, PR, and shelf recovery on top. $52K–$81K is what a mid-size brand pays to retrieve exactly what one lot touched, and nothing else. Against Cinderhaven's estimated annual EBITDA of ~$2.75M (11% of $25M revenue), the full-recall figure is three-plus years of earnings. The scoped figure is a bad month.

One footnote on the superseded brief: its $600K–$1.2M "Scenario B" guess turns out to sit near the shipped Scenario C ($491K–$764K) — the everything-case, not the shared-ingredient case. The pre-build instinct overshot B by an order of magnitude and accidentally priced the worst case. That is what modeling instead of asserting buys.

## The Gap Is Genealogy Data, Not Software

The graph looks like a visualization problem. It is not. The engagement-shaped problem is that lot genealogy does not exist as data at most $25M brands: it is trapped in co-packer batch records with inconsistent lot-code formats, lot codes mutate at repack, catch-weight items break unit math, and 3PL logs identify pallets (SSCC), not lots. Reconstructing the genealogy from those sources is the work. The tool demonstrates what the reconstructed data makes possible; the reconstruction is what Lailara sells.

## Audience and Offering

- **Primary:** the CEO, for whom Scenario B is an existential framing — one bad lot against a year of earnings.
- **Secondary:** the QA manager who runs the annual mock recall and knows the binder is theater, and the insurance broker.
- **Offering:** Traceability Readiness Assessment — fixed-fee, two weeks, $15K–$25K. KDE/CTE gap map against FSMA 204, lot-genealogy data assessment, a timed mock-recall drill with a blast-radius report, and a remediation roadmap. Client lift: batch record samples, a shipment log export, ERP production data, and one ops contact for 2–3 hours.

## Distribution

- **Portfolio:** "Risk & Traceability" engagement card on /work.
- **LinkedIn:** screen capture of the Scenario B fan-out. Draft lives at `drafts/linkedin-post-draft.md`, figures verified against the cache.
- **SEO:** FSMA 204 compliance for specialty food, mock recall exercise, lot traceability for small manufacturers. The searchers are the buyers.
- **Lead magnet:** the ten-question readiness checklist.

## Figure Ledger

Every number in this brief, and where it lives in the repo.

| Figure | Value | Source artifact |
|---|---|---|
| Scenario A scope | 1 SKU, 1 lot, 121 cases in channel, 3 retailers | `pipeline/cache/scenario_graphs.json` (scenario A `scope`) |
| Scenario A retrieval cost | $1,089–$1,694 | `pipeline/cache/scenario_graphs.json` (scenario A `cost_low`/`cost_high`) |
| Scenario B scope | 23 lots, 14 SKUs, 2 product lines (AS, SC), 6 retailers, 5,785 cases in channel, 23,842 sold through | `pipeline/cache/scenario_graphs.json` (scenario B `scope` + node inventory); `frontend/index.html` narrative |
| Blast-radius multiplier | 47.8× (5,785 ÷ 121 in-channel cases) | `pipeline/cache/scenario_graphs.json`; stated in `frontend/index.html` |
| Scenario B retrieval cost | $52,065–$80,990, shown as $52K–$81K | `pipeline/cache/scenario_graphs.json`; `frontend/index.html` margin-math block |
| Scenario C scope | 218 lots, 50 SKUs, 54,576 cases in channel, $491K–$764K | `pipeline/cache/scenario_graphs.json` (scenario C `scope`) |
| Cost model | $9–$14 per in-channel case: disposal $4 + freight $1.50 + retailer fees $2.50 + admin $1; direct retrieval only | `data/models/genealogy/fct_blast_radius_scope.sql` (duplicated in `pipeline/graph.py`) |
| Full-recall industry average | $10M+ | `frontend/index.html` hook + footnote (Deloitte/GMA/FMI, 2010) |
| Cinderhaven EBITDA | ~$2.75M (11% × $25M) | `frontend/index.html` margin-math block |
| FSMA 204 deadline | July 20, 2028 (FR Doc. 2025-14967 + Continuing Appropriations Act of 2026) | `frontend/index.html` evidence footnote |
| KDE/CTE coverage | 17 KDEs, 2 gaps (BOL reference docs) | `frontend/index.html` KDE table |
| Dataset baseline | 50 SKUs, 5 product lines, 6 retailers, seed=400, synthetic | `README.md` data contract |
| Offering price | $15K–$25K fixed-fee assessment | carried from the June 10 brief (business decision, not a computed figure) |
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                