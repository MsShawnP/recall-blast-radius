# FAILURES — recall-blast-radius

Approaches that didn't work and why. Read before repeating.

---

## 2026-06-10 — O(n²) BOM lookup in generate_genealogy.py

**What failed:** The batch loop that finds ingredient lots received before a batch's production date re-indexes the full `records["ingredient_lots"]` list on every iteration via a list comprehension index lookup — O(n²) over ~1,200 lots × ~600 batches = ~720K operations.

**Why:** Generator was written but not run before the session ended. Would have surfaced immediately on a test run.

**Fix:** Pre-build a `{ing_id: sorted [(date_str, lot_id), ...]}` dict before the batch loop. Use `bisect` or a simple filter on the sorted list to find candidates received before `prod_date`.

**Tags:** generator, performance, genealogy

---

## 2026-06-10 — Missing parent_id in fct_blast_radius recursive CTE

**What failed:** `fct_blast_radius.sql` outputs `(root_lot_id, node_type, node_id, label, depth, path)` but doesn't carry `parent_id` (the node_id of the prior step). The Dagster `genealogy_graph` asset and the FastAPI `/trace` route both need directed edges to build a NetworkX DiGraph — without `parent_id`, edge construction requires a second query or an array-unpacking pass on `path`.

**Why:** Designed the CTE for scope queries first (which only need node lists), then realized NetworkX needs explicit edges.

**Fix:** Add `br.node_id AS parent_id` (or `NULL` for the seed row) to every UNION ALL arm. One column addition, no structural change.

**Tags:** dbt, recursive-cte, networkx, schema

---

## 2026-06-10 — preview_screenshot consistently times out with D3 page

**What failed:** `mcp__Claude_Preview__preview_screenshot` timed out (30s) on every attempt — even after the API was running and the page was fully rendered.

**Why:** Initially the page was blocking on a `fetch()` call to a down API with no timeout, which froze the renderer. Fixed with `AbortController` (5s), but screenshots continued to time out — likely a renderer issue with D3 canvas or SVG paint cycle in the headless browser.

**Fix:** Use `preview_snapshot` instead for DOM/text verification, and `preview_eval` for targeted JS checks. Reserve screenshot attempts for pure layout checks where snapshot isn't enough.

**Tags:** preview, d3, debugging

---

## 2026-06-10 — `uvicorn` not in PATH on Windows (ENOENT)

**What failed:** `preview_start` with `runtimeExecutable: "uvicorn"` failed: `spawn uvicorn ENOENT`. uvicorn is installed (importable in Python) but its script isn't on the system PATH.

**Why:** Windows Store Python installs put scripts in a user-local path that isn't always on PATH.

**Fix:** Use `python -m uvicorn` — set `runtimeExecutable: "python"` and add `"-m", "uvicorn"` as the first two `runtimeArgs`. Works reliably across environments.

**Tags:** windows, uvicorn, preview, launch-json

---

## 2026-06-10 — Silent empty scope panel from wrong argument to renderScopePanel

**What failed:** Scope panel rendered completely empty with no console error. `renderScopePanel(scenario)` was called with the full `ScenarioGraph` object; inside the function `const { scope } = scenario` returned `undefined` because scope is at `scenario.result.scope`.

**Why:** `renderGraph` correctly received `scenario.result`; `renderScopePanel` did not — asymmetric call sites, no type enforcement, JS destructuring fails silently on undefined.

**Fix:** `renderScopePanel(scenario.result)` — one word change at the call site.

**Tags:** frontend, javascript, silent-bug, destructuring

---

## 2026-06-10 — Process: wrote full generator before running minimal version

**What failed:** Wrote ~200 lines of seed generator before executing even a 10-batch smoke test. The O(n²) bug and other likely issues went undetected.

**Lesson:** For generators and data pipelines, write the skeleton → run it with n=10 → verify counts and shape → then scale up. "Write then run" loses cheap feedback from the first run.

**Tags:** process, generators
