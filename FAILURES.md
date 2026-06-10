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

## 2026-06-10 — Process: wrote full generator before running minimal version

**What failed:** Wrote ~200 lines of seed generator before executing even a 10-batch smoke test. The O(n²) bug and other likely issues went undetected.

**Lesson:** For generators and data pipelines, write the skeleton → run it with n=10 → verify counts and shape → then scale up. "Write then run" loses cheap feedback from the first run.

**Tags:** process, generators
