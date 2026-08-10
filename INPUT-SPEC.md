# Recall Blast Radius — Client Data Input Specification

Recall Blast Radius traces a recall through your **lot genealogy**: pick a seed
lot, propagate forward, and scope the impact — finished-goods lots affected,
cases still in channel, direct-cost range, and the trading-partner notification
list. It is a graph problem, so it reads two files (not the POS layer).

Column names are canonical; map your headers in `engagement.yml`. Identifiers are
read as **text**. A missing required column yields a branded Data Readiness
Report, not a result.

## §Genealogy — the forward contamination graph (required)
One row per parent→child edge in your lot genealogy (ingredient → batch →
finished-goods lot → …).

| Column | Type | Required | Used for |
|---|---|---|---|
| `parent_lot_id` | identifier (text) | optional | upstream lot; **blank = a root node** |
| `child_lot_id` | identifier (text) | **required** | downstream lot/node |
| `child_type` | string | **required** | node type of the child (`ingredient_lot`, `batch`, `fg_lot`, `case`, `shipment`, `retailer`) — only `fg_lot` nodes carry cases |

## §ShipTo — where the finished-goods lots went (required)
| Column | Type | Required | Used for |
|---|---|---|---|
| `fg_lot_id` | identifier (text) | **required** | joins to `fg_lot` nodes in the genealogy |
| `ship_to` | string | **required** | retailer / DC — the notification list |
| `cases_in_channel` | number ≥ 0 | **required** | recallable cases; drives the cost range |
| `cases_shipped` | number ≥ 0 | optional | shipped total |
| `cases_sold_through` | number ≥ 0 | optional | already sold through |

## Seed lot (required)
Set the lot to trace from — `--seed <lot_id>` or `basis.seed_lot` in
`engagement.yml`. The scope is every finished-goods lot reachable forward from
the seed, and the ship-to records for those lots.

Direct cost = cases in channel × **$9–$14 / case** (disposal + freight + retailer
handling + admin) — the same constants the demo uses.

## Column mapping (`engagement.yml`)
```yaml
client: {name: Your Brand}
engagement: {id: YB-2026-08}
as_of_date: 2026-06-27
basis:
  seed_lot: ING-001
inputs:
  genealogy: client-data/genealogy.csv
  shipto: client-data/shipto.csv
columns:
  child_lot_id: "Child Lot"
  child_type: "Node Type"
  fg_lot_id: "FG Lot"
  ship_to: "Customer"
  cases_in_channel: "Cases In Channel"
```
