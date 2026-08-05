"""Client-mode CLI for Recall Blast Radius.

Traces a client's own lot genealogy and ship-to records to scope a recall: pick
a seed lot, propagate forward through the genealogy graph, and report the blast
radius — finished-goods lots affected, cases still in channel, direct-cost range,
and the trading-partner notification list.

Recall is a graph problem, not a POS-scan problem, so it does NOT use the shared
POS-intake layer; it reads two client files with the shared ``lailara_engagement``
scaffold (tolerant intake + preflight + provenance):

  * **genealogy** edges — parent_lot_id → child_lot_id (child_type) — the forward
    contamination graph;
  * **ship-to** records — fg_lot_id, ship_to, cases_in_channel/shipped/sold —
    where the finished-goods lots went.

A missing required column blocks with a branded Data Readiness Report; a clean
run writes a draft-watermarked, provenance-footed **Recall Blast Radius** scope
(HTML) + the notification list (CSV) to ``client-output/`` only.

Usage:
    python client_mode.py --config engagement.yml --seed ING-001 [--out client-output] [--final]
"""

from __future__ import annotations

import argparse
import html
from pathlib import Path

import networkx as nx

from lailara_engagement import (
    ColumnSpec,
    PreflightSpec,
    build_provenance,
    load_config,
    read_table,
    run_preflight,
    validation_status_label,
    write_report,
)
from lailara_engagement import palette as P
from lailara_engagement.provenance import Provenance
from lailara_engagement.pos import to_frame

TOOL = "recall-blast-radius"
TOOL_VERSION = "1.0"

# Direct per-case low/high cost constants — same as pipeline/graph.py.
COST_LOW_PER_CASE = 9.0
COST_HIGH_PER_CASE = 14.0


def _genealogy_spec() -> PreflightSpec:
    return PreflightSpec(tool=TOOL, version=TOOL_VERSION, columns=[
        ColumnSpec(name="parent_lot_id", dtype="identifier", required=False, allow_blank=True,
                   description="upstream lot; blank = a root node", spec_ref="INPUT-SPEC §Genealogy"),
        ColumnSpec(name="child_lot_id", dtype="identifier", required=True,
                   description="downstream lot/node id", spec_ref="INPUT-SPEC §Genealogy"),
        ColumnSpec(name="child_type", dtype="string", required=True,
                   description="node type of the child (ingredient_lot/batch/fg_lot/...)",
                   spec_ref="INPUT-SPEC §Genealogy"),
    ])


def _shipto_spec() -> PreflightSpec:
    return PreflightSpec(tool=TOOL, version=TOOL_VERSION, columns=[
        ColumnSpec(name="fg_lot_id", dtype="identifier", required=True,
                   description="finished-goods lot shipped", spec_ref="INPUT-SPEC §ShipTo"),
        ColumnSpec(name="ship_to", dtype="string", required=True,
                   description="retailer / DC the lot shipped to", spec_ref="INPUT-SPEC §ShipTo"),
        ColumnSpec(name="cases_in_channel", dtype="number", required=True, not_negative=True,
                   description="cases still in channel (recallable)", spec_ref="INPUT-SPEC §ShipTo"),
        ColumnSpec(name="cases_shipped", dtype="number", required=False, allow_blank=True,
                   not_negative=True, description="cases shipped", spec_ref="INPUT-SPEC §ShipTo"),
        ColumnSpec(name="cases_sold_through", dtype="number", required=False, allow_blank=True,
                   not_negative=True, description="cases sold through", spec_ref="INPUT-SPEC §ShipTo"),
    ])


def build_graph_from_edges(edges) -> nx.DiGraph:
    """DiGraph from client genealogy edges; child node carries its type."""
    G = nx.DiGraph()
    for _, r in edges.iterrows():
        child, ctype = str(r["child_lot_id"]).strip(), str(r["child_type"]).strip()
        G.add_node(child, type=ctype)
        parent = str(r["parent_lot_id"]).strip()
        if parent:
            if parent not in G:
                G.add_node(parent, type="")
            G.add_edge(parent, child)
    return G


def trace_scope(G: nx.DiGraph, shipments, seed: str) -> dict:
    """Forward blast-radius scope for a seed lot."""
    if seed not in G:
        reachable = {seed}
    else:
        reachable = nx.descendants(G, seed) | {seed}
    fg_lots = {n for n in reachable if G.nodes.get(n, {}).get("type") == "fg_lot"}
    affected = shipments[shipments["fg_lot_id"].isin(fg_lots)]
    in_channel = float(affected["cases_in_channel"].sum()) if not affected.empty else 0.0
    sold = float(affected["cases_sold_through"].sum()) if "cases_sold_through" in affected else 0.0
    notification = sorted(affected["ship_to"].dropna().astype(str).unique())
    return {
        "seed": seed,
        "reachable_nodes": len(reachable),
        "lots_affected": len(fg_lots),
        "cases_in_channel": round(in_channel, 2),
        "cases_sold_through": round(sold, 2),
        "cost_low": round(in_channel * COST_LOW_PER_CASE, 2),
        "cost_high": round(in_channel * COST_HIGH_PER_CASE, 2),
        "notification_list": notification,
    }


def _fmt_dollars(v):
    return "—" if v is None else f"${v:,.0f}"


def _deliverable_html(config, scope, provenance: Provenance, limitations, *, draft: bool) -> str:
    esc = html.escape
    draft_class = " ll-draft" if draft else ""
    notif = "".join(f"<li>{esc(n)}</li>" for n in scope["notification_list"]) or "<li>(none)</li>"
    lim = "".join(f"<li>{esc(x)}</li>" for x in limitations)
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1">
<title>Recall Blast Radius — {esc(config.client_name)}</title><style>{_css(draft)}</style></head>
<body class="{draft_class.strip()}"><main class=ll-page>
<header class=ll-header>
  <div class=ll-eyebrow>Lailara LLC · Recall Blast Radius</div>
  <h1 class=ll-title>Recall Blast Radius — Lot {esc(scope['seed'])}</h1>
  <div class=ll-client>
    <div><span class=ll-k>Client</span> {esc(config.client_name)}</div>
    <div><span class=ll-k>Engagement</span> {esc(config.engagement_id)}</div>
    <div><span class=ll-k>As of</span> {esc(config.as_of_date.isoformat())}</div>
    <div><span class=ll-k>Prepared by</span> {esc(config.prepared_by)}</div>
  </div>
</header>
<section class=ll-banner>
  <div class=ll-score>{scope['lots_affected']:,} finished-goods lots · {scope['cases_in_channel']:,.0f} cases in channel</div>
  <div>direct cost {_fmt_dollars(scope['cost_low'])}–{_fmt_dollars(scope['cost_high'])}
       · {len(scope['notification_list'])} trading partners to notify
       · {scope['cases_sold_through']:,.0f} cases already sold through</div>
  <div class=ll-basis>Basis: forward genealogy trace from the seed lot; cost = cases in channel
       × ${COST_LOW_PER_CASE:.0f}–${COST_HIGH_PER_CASE:.0f}/case (disposal + freight + handling + admin)</div>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Notification list</h2>
  <ul class=ll-limitations>{notif}</ul>
</section>
<section class=ll-section>
  <h2 class=ll-h2>Data limitations</h2>
  <ul class=ll-limitations>{lim}</ul>
</section>
{provenance.to_html()}
</main></body></html>"""


def _css(draft: bool) -> str:
    draft_css = (
        ".ll-draft::before{content:'DRAFT';position:fixed;top:50%;left:50%;"
        "transform:translate(-50%,-50%) rotate(-32deg);font-family:var(--s);"
        "font-size:22vw;font-weight:700;color:rgba(204,16,10,.06);z-index:0;"
        "pointer-events:none;white-space:nowrap}" if draft else ""
    )
    return f"""
:root{{--s:{P.LL_SERIF};--f:{P.LL_SANS}}}
*{{box-sizing:border-box}}
body{{margin:0;background:{P.LL_CANVAS};color:{P.LL_TEXT};font-family:var(--f);line-height:1.6}}
.ll-page{{position:relative;z-index:1;max-width:{P.LL_MAX_WIDTH};margin:0 auto;padding:48px 24px}}
.ll-header{{border-bottom:1px solid {P.LL_GRIDLINE};padding-bottom:24px;margin-bottom:24px}}
.ll-eyebrow{{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:{P.LL_RED};font-weight:600}}
.ll-title{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:32px;margin:8px 0 16px}}
.ll-client{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px 24px;font-size:14px}}
.ll-k{{display:block;color:{P.LL_TEXT_SEC};font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.ll-banner{{border-radius:2px;padding:16px 20px;margin-bottom:32px;background:{P.LL_RED_SURFACE};color:{P.LL_RED_DARK}}}
.ll-score{{font-family:var(--s);font-weight:700;font-size:22px}}
.ll-basis{{font-size:12px;color:{P.LL_TEXT_SEC};margin-top:8px}}
.ll-section{{margin:0 0 32px}}
.ll-h2{{font-family:var(--s);font-weight:700;color:{P.LL_INK};font-size:22px;
margin:0 0 12px;padding-bottom:6px;border-bottom:1px solid {P.LL_GRIDLINE}}}
.ll-limitations{{margin:0;padding-left:20px}}.ll-limitations li{{margin-bottom:6px}}
.ll-provenance{{margin-top:40px;background:{P.LL_CARD_BG};color:{P.LL_CARD_TEXT};
padding:20px 24px;border-radius:2px;font-size:13px}}
.ll-prov-title{{font-family:var(--s);font-weight:700;font-size:16px;margin-bottom:8px}}
.ll-provenance div{{margin-bottom:4px;color:{P.LL_CARD_SUBTITLE}}}
.ll-provenance strong{{color:{P.LL_CARD_TEXT}}}
.ll-prov-inputs{{width:100%;border-collapse:collapse;margin-top:8px}}
.ll-prov-inputs th{{text-align:left;border-bottom:1px solid rgba(255,255,255,.12);padding:4px 8px;color:{P.LL_CARD_MUTED}}}
.ll-prov-inputs td{{padding:4px 8px;border-bottom:1px solid rgba(255,255,255,.08);color:{P.LL_CARD_SUBTITLE}}}
.ll-prov-brand{{margin-top:12px;font-family:var(--s);color:{P.LL_CARD_MUTED}}}
{draft_css}
@media print{{body{{background:#fff}}}}
"""


def run(config_path: str, out_dir: str, args, *, final: bool = False) -> dict:
    config = load_config(config_path)
    ci = config.raw.get("inputs") or {}
    genealogy_path = args.genealogy or ci.get("genealogy")
    shipto_path = args.shipto or ci.get("shipto") or ci.get("shipments")
    seed = args.seed or (config.basis or {}).get("seed_lot")
    if not (genealogy_path and shipto_path):
        raise SystemExit("missing required input(s): genealogy and/or shipto.")
    if not seed:
        raise SystemExit("no seed lot — pass --seed or set basis.seed_lot in engagement.yml.")

    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    specs = {"genealogy": _genealogy_spec(), "shipto": _shipto_spec()}
    paths = {"genealogy": genealogy_path, "shipto": shipto_path}
    reads, reports, frames = {}, {}, {}
    for key, spec in specs.items():
        read = read_table(paths[key])
        report = run_preflight(read, spec, config)
        reads[key], reports[key] = read, report
        frames[key] = to_frame(read, report, spec) if report.passed else None

    blocked = {k: r for k, r in reports.items() if not r.passed}
    provenance = build_provenance(
        tool=TOOL, tool_version=TOOL_VERSION, inputs=[reads[k] for k in specs], config=config,
        validation_status=validation_status_label("failed" if blocked else "clean",
                                                   sum(r.n_warnings for r in reports.values())),
        extra={"Seed lot": str(seed)})
    if blocked:
        written = {}
        for key, report in blocked.items():
            p = write_report(report, config, str(out), provenance=provenance, draft=not final,
                             basename=f"data-readiness-{key}",
                             title=f"Recall Data Readiness Report — {key}")
            written[key] = p["html"]
        return {"status": "blocked", "blocked_files": list(blocked), "readiness_reports": written}

    G = build_graph_from_edges(frames["genealogy"])
    scope = trace_scope(G, frames["shipto"], str(seed))

    limitations = []
    for key, report in reports.items():
        for f in report.findings:
            if f.severity == "warning":
                limitations.append(f"[{key}] {f.message}")
    if str(seed) not in G:
        limitations.append(f"Seed lot {seed} not found in the genealogy — scope is empty; "
                           "check the seed id and that it appears as a parent or child.")
    if not limitations:
        limitations.append("No warnings — both inputs passed preflight cleanly.")

    csv_path = out / "notification-list.csv"
    import pandas as pd
    pd.DataFrame({"ship_to": scope["notification_list"]}).to_csv(csv_path, index=False)
    html_path = out / "recall-blast-radius.html"
    html_path.write_text(_deliverable_html(config, scope, provenance, limitations, draft=not final),
                         encoding="utf-8")
    return {"status": "ok", **{k: scope[k] for k in ("lots_affected", "cases_in_channel", "cost_high")},
            "n_notify": len(scope["notification_list"]), "report": str(html_path),
            "exceptions_csv": str(csv_path), "n_warnings": sum(r.n_warnings for r in reports.values())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="recall client mode")
    ap.add_argument("--config", required=True)
    ap.add_argument("--genealogy"); ap.add_argument("--shipto"); ap.add_argument("--seed")
    ap.add_argument("--out", default="client-output"); ap.add_argument("--final", action="store_true")
    args = ap.parse_args(argv)
    result = run(args.config, args.out, args, final=args.final)
    if result["status"] == "blocked":
        print("BLOCKED — data not ready. Readiness report(s):")
        for key, path in result["readiness_reports"].items():
            print(f"  {key}: {path}")
        return 3
    print(f"{result['lots_affected']} lots · {result['cases_in_channel']:,.0f} cases in channel · "
          f"cost up to {_fmt_dollars(result['cost_high'])} · {result['n_notify']} to notify")
    print(f"report -> {result['report']}\ncsv    -> {result['exceptions_csv']}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
