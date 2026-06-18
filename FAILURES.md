# FAILURES — recall-blast-radius

Approaches that didn't work and why. Read before repeating.

---

## 2026-06-11 — Filesystem search for lailara-website repo was slow

**What failed:** Multiple `find` / `glob` / `grep` searches across `projects/active`, `projects/published`, and `projects/reference` to locate the lailara-website source. Took several rounds before finding it at `C:\Users\mssha\projects\reference\lailara-website\site`.

**Why:** The repo lives in `reference/`, not `active/` or `published/`, which isn't the natural search order.

**Fix:** Use `gh repo list MsShawnP` first when looking for any repo — name is instantly visible and avoids filesystem iteration.

**Tags:** workflow, repo-discovery, lailara-website

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

---

## 2026-06-11 — import.meta.env is a Vite bundler pattern, not a browser primitive

**What failed:** `const API_BASE = import.meta.env?.VITE_API_BASE ?? 'http://localhost:8000/api'` — in a plain static site with no bundler, `import.meta.env` is always `undefined` at runtime. The `??` fallback to localhost always fired, so production would silently hit the local API instead of Fly.io.

**Why:** Pattern copied from Vite project conventions. Without a build step, the bundler never replaces `import.meta.env.VITE_API_BASE` with the actual value.

**Fix:** For no-build static sites, use hostname detection: `const LOCAL = ['localhost','127.0.0.1'].includes(window.location.hostname); const API_BASE = LOCAL ? '...' : '...'`. Zero config, works everywhere.

**Tags:** frontend, deployment, static-site, vite, api-url

---

## 2026-06-11 — wrangler pages domain add does not exist in wrangler v4

**What failed:** `npx wrangler pages domain add recall-blast-radius recall.lailarallc.com` — command not found. Wrangler v4 has no `pages domain` subcommand.

**Why:** Docs or memory from an older wrangler version. The `pages` command group in v4 only has: `dev`, `functions`, `project`, `deployment`, `deploy`, `secret`, `download`.

**Fix:** Use the Cloudflare REST API directly: `POST /accounts/{id}/pages/projects/{name}/domains` with `{"name": "recall.lailarallc.com"}`. Requires `CLOUDFLARE_API_TOKEN` env var (already available). Then create the CNAME DNS record separately via `POST /zones/{zone_id}/dns_records`.

**Tags:** cloudflare, wrangler, deployment, custom-domain

---

## 2026-06-18 — Playfair Display clips at large sizes with line-height: 1

**What failed:** `line-height: 1` on Playfair Display at 64px (`.hook-stat`), 36px (`.scope-headline`), and 28px (`.margin-math__value`) caused visible clipping — 4px overflow on the largest, 2px on the smaller two. ui-review-skill flagged all three as layout FAILs.

**Why:** Playfair Display has taller cap-height and descender metrics than web-safe serifs. `line-height: 1` (exactly the em-square) clips the top and bottom at any size above ~20px.

**Fix:** Set `line-height: 1.1` minimum for any Playfair Display element above 20px. For normal body text the default `1.5` is fine; it's only display-size numbers and headings that need the explicit floor.

**Process sub-failure:** Fixed `.hook-stat` and `.scope-headline` first without grepping for all `line-height: 1` instances — required a second redeploy when `.margin-math__value` also failed. Grep first, fix all at once.

**Tags:** css, typography, playfair-display, ui-review, deployment

---

## 2026-06-11 — wrangler pages deploy fails on dirty working tree without flag

**What failed:** `npx wrangler pages deploy frontend --project-name recall-blast-radius` exited with an error when the working tree had uncommitted changes.

**Why:** Wrangler treats a dirty git working tree as an error by default (it wants a clean source association).

**Fix:** Pass `--commit-dirty=true` to override: `npx wrangler pages deploy frontend --project-name recall-blast-radius --commit-dirty=true`.

**Tags:** cloudflare, wrangler, deployment, git
