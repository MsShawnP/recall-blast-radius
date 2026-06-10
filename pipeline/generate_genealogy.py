"""
Genealogy seed data generator — seed=400 (isolated from platform streams).

Generates:
  - 3 co-packers with distinct lot-code formats
  - ~25 ingredients (spices, sauce bases, acids, packaging)
  - ~1,200 ingredient lots over 3-year window (2023–2025)
  - ~600 production batches (50 SKUs × ~4 runs/yr × 3 yr)
  - ~600 FG lots (1:1 with batches for this model)
  - ~2,400 shipment–lot links (each FG lot ships to 2–6 shipments)
  - 3 packaging lots (one per scenario C variant)
  - 3 preset scenario records (A, B, C)

Throughput constraint: must reconcile with canonical $25M revenue.
  ~357K cases/year at $70/case average → ~1,800 cases/batch average.

Lot-code realism:
  CP-EAST:    Julian date + line code  → "24312-L3"   (day 312 of 2024, line 3)
  CP-WEST:    YYYYMMDD + seq          → "20240312-042"
  CP-CENTRAL: YYWww + seq             → "24W12-089"   (2024 week 12, seq 089)

The critical realism detail: co_packer_lot_code ≠ internal_lot_code on fg_lots.
Cinderhaven assigns their own ERP code; the 3PL logs the co-packer code.
The mapping between the two is the engagement.
"""

import random
import hashlib
from datetime import date, timedelta


SEED = 400
rng = random.Random(SEED)

# ---------------------------------------------------------------------------
# Canonical constants (from CINDERHAVEN_CANONICAL.md)
# ---------------------------------------------------------------------------
SKUS = [
    f"CHP-{line}-{n:03d}"
    for line in ["AS", "PS", "SC", "DG", "SB"]
    for n in range(1, 11)
]

RETAILERS = [
    ("RET-WALMART",    "Walmart",       180),
    ("RET-COSTCO",     "Costco",         60),
    ("RET-WHOLEFOODS", "Whole Foods",   120),
    ("RET-SPROUTS",    "Sprouts",        90),
    ("RET-KROGER",     "Kroger",        150),
    ("RET-REGIONAL",   "Regional Group", 40),
]

DATA_START = date(2023, 1, 1)
DATA_END   = date(2026, 1, 2)

CASES_PER_YEAR  = 357_000
AVG_CASES_BATCH = 1_800

# ---------------------------------------------------------------------------
# Co-packers
# ---------------------------------------------------------------------------
CO_PACKERS = [
    {
        "co_packer_id":    "CP-EAST",
        "name":            "Eastern Traditions Co-Packing",
        "lot_code_format": "julian_line",
        "primary_lines":   ["AS", "SC"],
    },
    {
        "co_packer_id":    "CP-WEST",
        "name":            "Pacific Ridge Foods Manufacturing",
        "lot_code_format": "sequential_date",
        "primary_lines":   ["PS", "DG"],
    },
    {
        "co_packer_id":    "CP-CENTRAL",
        "name":            "Heartland Food Solutions",
        "lot_code_format": "yearweek_seq",
        "primary_lines":   ["SB", "AS"],
    },
]

# ---------------------------------------------------------------------------
# Ingredients — realistic for a hot sauce / specialty condiment brand
# ---------------------------------------------------------------------------
INGREDIENTS = [
    # Spices / dried goods
    ("ING-001", "Chili Flakes",          "spice",       True,  "lbs"),
    ("ING-002", "Smoked Paprika",        "spice",       False, "lbs"),
    ("ING-003", "Cumin",                 "spice",       False, "lbs"),
    ("ING-004", "Garlic Powder",         "spice",       False, "lbs"),
    ("ING-005", "Black Pepper",          "spice",       False, "lbs"),
    ("ING-006", "Cayenne Pepper",        "spice",       True,  "lbs"),
    ("ING-007", "Onion Powder",          "spice",       False, "lbs"),
    # Sauce bases / liquids
    ("ING-010", "Distilled White Vinegar","acid",       False, "gal"),
    ("ING-011", "Apple Cider Vinegar",   "acid",        False, "gal"),
    ("ING-012", "Tomato Paste",          "sauce_base",  True,  "lbs"),
    ("ING-013", "Roasted Red Pepper Puree","sauce_base",True,  "lbs"),
    ("ING-014", "Habanero Mash",         "sauce_base",  True,  "lbs"),
    # Sweeteners / stabilizers
    ("ING-020", "Cane Sugar",            "sweetener",   False, "lbs"),
    ("ING-021", "Honey (Dry)",           "sweetener",   False, "lbs"),
    ("ING-022", "Xanthan Gum",           "stabilizer",  False, "lbs"),
    ("ING-023", "Salt",                  "mineral",     False, "lbs"),
    # Packaging
    ("ING-030", "5oz Glass Bottle",      "packaging",   False, "units"),
    ("ING-031", "Label Stock (4-color)", "packaging",   False, "units"),
    ("ING-032", "Cardboard Shipper Case","packaging",   False, "units"),
    ("ING-033", "Tamper-evident Seal",   "packaging",   False, "units"),
    ("ING-034", "10oz Glass Bottle",     "packaging",   False, "units"),
    ("ING-035", "2oz Snack Pouch Film",  "packaging",   False, "units"),
]

# Which ingredients map to which product lines (for realistic BOM)
LINE_INGREDIENTS = {
    "AS": ["ING-001", "ING-006", "ING-012", "ING-013", "ING-010", "ING-023",
           "ING-022", "ING-030", "ING-031", "ING-032"],
    "SC": ["ING-001", "ING-002", "ING-011", "ING-014", "ING-020", "ING-023",
           "ING-022", "ING-030", "ING-031", "ING-032"],
    "PS": ["ING-003", "ING-004", "ING-005", "ING-007", "ING-023",
           "ING-032", "ING-035"],
    "DG": ["ING-002", "ING-003", "ING-004", "ING-005", "ING-006", "ING-007",
           "ING-023", "ING-032", "ING-035"],
    "SB": ["ING-021", "ING-022", "ING-004", "ING-006", "ING-023",
           "ING-033", "ING-035", "ING-032"],
}

# ---------------------------------------------------------------------------
# Lot-code generators (realistic format per co-packer)
# ---------------------------------------------------------------------------

def julian_line_code(d: date, line: int) -> str:
    """CP-EAST: YYDDD-Ln (e.g. 24312-L3)"""
    return f"{d.strftime('%y')}{d.timetuple().tm_yday:03d}-L{line}"


def sequential_date_code(d: date, seq: int) -> str:
    """CP-WEST: YYYYMMDD-NNN (e.g. 20240312-042)"""
    return f"{d.strftime('%Y%m%d')}-{seq:03d}"


def yearweek_seq_code(d: date, seq: int) -> str:
    """CP-CENTRAL: YYWww-NNN (e.g. 24W12-089)"""
    week = d.isocalendar()[1]
    return f"{d.strftime('%y')}W{week:02d}-{seq:03d}"


LOT_CODE_FNS = {
    "julian_line":     lambda d, seq: julian_line_code(d, rng.randint(1, 4)),
    "sequential_date": sequential_date_code,
    "yearweek_seq":    yearweek_seq_code,
}

# ---------------------------------------------------------------------------
# Internal ERP lot code (different from co-packer code — this is the trap)
# ---------------------------------------------------------------------------

def internal_lot_code(sku_id: str, production_date: date, seq: int) -> str:
    """Cinderhaven ERP assigns: CHP-{line}-{NNN}-{YYYYMMDD}-{seq:02d}"""
    line = sku_id.split("-")[1]
    num  = sku_id.split("-")[2]
    return f"LOT-{line}{num}-{production_date.strftime('%Y%m%d')}-{seq:02d}"


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_all():
    """
    Returns a dict of lists, each list being rows for one table.
    Call this from the Dagster asset or a standalone script.
    """

    records = {
        "co_packers":          CO_PACKERS,
        "ingredients":         [],
        "ingredient_lots":     [],
        "production_batches":  [],
        "batch_ingredient_map":[],
        "fg_lots":             [],
        "packaging_lots":      [],
        "batch_packaging_map": [],
        "shipment_lot_map":    [],
        "scenarios":           [],
        "product_master":      [],
        "retailers":           list({"retailer_id": r[0], "retailer_name": r[1],
                                     "store_doors": r[2]} for r in RETAILERS),
        "shipments":           [],
    }

    # Ingredients
    for ing in INGREDIENTS:
        records["ingredients"].append({
            "ingredient_id":  ing[0],
            "name":           ing[1],
            "category":       ing[2],
            "is_ftl_upstream": ing[3],
            "unit":           ing[4],
        })

    # Product master stubs (canonical 50 SKUs)
    sku_info = {
        "AS": ("Artisan Sauce",      "AS"),
        "PS": ("Pantry Staple",      "PS"),
        "SC": ("Specialty Condiment","SC"),
        "DG": ("Dried Good",         "DG"),
        "SB": ("Snack Bite",         "SB"),
    }
    for sku_id in SKUS:
        line = sku_id.split("-")[1]
        num  = int(sku_id.split("-")[2])
        records["product_master"].append({
            "sku_id":           sku_id,
            "sku_name":         f"{sku_info[line][0]} #{num:02d}",
            "product_line":     line,
            "cases_per_pallet": 60,
        })

    # Ingredient lots — ~400/year, 3-year window = 1200 lots
    # Pre-generate a pool; batches will draw from recent lots
    cp_by_format = {cp["co_packer_id"]: cp for cp in CO_PACKERS}
    ing_lot_pool: dict[str, list[str]] = {ing[0]: [] for ing in INGREDIENTS}

    n_days = (DATA_END - DATA_START).days
    lot_seq_counter: dict[str, int] = {}

    for _ in range(1_200):
        ing = rng.choice(INGREDIENTS)
        ing_id = ing[0]
        cp = rng.choice([c for c in CO_PACKERS
                         if ing[2] != "packaging"])  # packaging lots handled separately
        d = DATA_START + timedelta(days=rng.randint(0, n_days - 90))
        lot_seq_counter[ing_id] = lot_seq_counter.get(ing_id, 0) + 1
        seq = lot_seq_counter[ing_id]

        cp_code_fn = LOT_CODE_FNS[cp["lot_code_format"]]
        cp_code    = cp_code_fn(d, seq)
        lot_id     = f"{ing_id}-{d.strftime('%y%m%d')}-{seq:03d}"

        records["ingredient_lots"].append({
            "ingredient_lot_id":  lot_id,
            "ingredient_id":      ing_id,
            "co_packer_id":       cp["co_packer_id"],
            "supplier_name":      f"Supplier-{hashlib.md5(ing_id.encode()).hexdigest()[:4].upper()}",
            "supplier_lot_code":  f"SUP-{rng.randint(10000, 99999)}",
            "co_packer_lot_code": cp_code,
            "quantity_lbs":       round(rng.uniform(200, 2000), 2),
            "received_date":      d.isoformat(),
            "best_by_date":       (d + timedelta(days=rng.randint(365, 730))).isoformat(),
            "status":             "consumed",
        })
        ing_lot_pool[ing_id].append(lot_id)

    # Production batches — ~600 over 3 years
    sku_cp_map = {}
    for sku_id in SKUS:
        line = sku_id.split("-")[1]
        line_cps = [cp["co_packer_id"] for cp in CO_PACKERS
                    if line in cp["primary_lines"]]
        sku_cp_map[sku_id] = rng.choice(line_cps) if line_cps else rng.choice(
            [cp["co_packer_id"] for cp in CO_PACKERS])

    batch_seq = 0
    shipment_seq = 0

    for sku_id in SKUS:
        line   = sku_id.split("-")[1]
        cp_id  = sku_cp_map[sku_id]
        cp     = cp_by_format[cp_id]
        n_batches = rng.randint(10, 14)    # ~4/yr × 3 yr with variance

        for b in range(n_batches):
            batch_seq += 1
            prod_date  = DATA_START + timedelta(
                days=rng.randint(0, (DATA_END - DATA_START).days - 30))
            n_cases    = rng.randint(1_200, 2_400)

            cp_batch   = LOT_CODE_FNS[cp["lot_code_format"]](prod_date, batch_seq)
            batch_id   = f"BTH-{cp_id}-{prod_date.strftime('%y%m%d')}-{batch_seq:04d}"

            records["production_batches"].append({
                "batch_id":             batch_id,
                "sku_id":               sku_id,
                "co_packer_id":         cp_id,
                "production_date":      prod_date.isoformat(),
                "batch_quantity_cases": n_cases,
                "co_packer_batch_code": cp_batch,
                "status":               "shipped",
            })

            # Assign ingredient lots (BOM)
            bom_ings = LINE_INGREDIENTS.get(line, [])
            for ing_id in bom_ings:
                candidates = [l for l in ing_lot_pool.get(ing_id, [])
                              if records["ingredient_lots"][[r["ingredient_lot_id"]
                                  for r in records["ingredient_lots"]].index(l)]
                                  ["received_date"] <= prod_date.isoformat()]
                if not candidates:
                    continue
                chosen_lot = rng.choice(candidates[-20:])  # bias recent lots
                records["batch_ingredient_map"].append({
                    "batch_id":           batch_id,
                    "ingredient_lot_id":  chosen_lot,
                    "quantity_used_lbs":  round(rng.uniform(50, 400), 2),
                })

            # FG lot (1:1 with batch for this model)
            fg_lot_id     = f"FGL-{sku_id}-{prod_date.strftime('%y%m%d')}-{batch_seq:04d}"
            int_lot_code  = internal_lot_code(sku_id, prod_date, b + 1)
            cp_fg_code    = LOT_CODE_FNS[cp["lot_code_format"]](prod_date, batch_seq + 1000)

            records["fg_lots"].append({
                "fg_lot_id":           fg_lot_id,
                "batch_id":            batch_id,
                "sku_id":              sku_id,
                "internal_lot_code":   int_lot_code,
                "co_packer_lot_code":  cp_fg_code,
                "quantity_cases":      n_cases,
                "production_date":     prod_date.isoformat(),
                "best_by_date":        (prod_date + timedelta(days=rng.randint(365, 730))).isoformat(),
                "status":              "sold_through",
            })

            # Shipments from this FG lot (2–6 per lot)
            n_ships     = rng.randint(2, 6)
            cases_left  = n_cases
            retailers   = rng.choices([r[0] for r in RETAILERS], k=n_ships)

            for ret_id in retailers:
                if cases_left <= 0:
                    break
                shipment_seq += 1
                ship_cases = min(rng.randint(100, 600), cases_left)
                ship_date  = prod_date + timedelta(days=rng.randint(14, 45))
                ship_id    = f"SHP-{prod_date.strftime('%y%m%d')}-{shipment_seq:05d}"

                records["shipments"].append({
                    "shipment_id":   ship_id,
                    "order_id":      f"ORD-{shipment_seq:06d}",
                    "retailer_id":   ret_id,
                    "ship_date":     ship_date.isoformat(),
                    "cases_shipped": ship_cases,
                })

                in_channel = int(ship_cases * rng.uniform(0.05, 0.35))
                records["shipment_lot_map"].append({
                    "shipment_id":       ship_id,
                    "fg_lot_id":         fg_lot_id,
                    "cases_shipped":     ship_cases,
                    "cases_in_channel":  in_channel,
                    "cases_sold_through": ship_cases - in_channel,
                })
                cases_left -= ship_cases

    # ---------------------------------------------------------------------------
    # Packaging lots (for Scenario C)
    # ---------------------------------------------------------------------------
    pkg_lots = [
        {
            "packaging_lot_id": "PKG-LABEL-230110-001",
            "packaging_type":   "label",
            "supplier_name":    "Summit Label Solutions",
            "lot_code":         "SLS-23010-A",
            "quantity_units":   150_000,
            "received_date":    "2023-01-10",
        },
        {
            "packaging_lot_id": "PKG-LABEL-240115-001",
            "packaging_type":   "label",
            "supplier_name":    "Summit Label Solutions",
            "lot_code":         "SLS-24015-B",
            "quantity_units":   200_000,
            "received_date":    "2024-01-15",
        },
    ]
    records["packaging_lots"] = pkg_lots

    # Assign packaging lots to batches (each batch uses labels from the
    # nearest preceding label lot by received_date)
    for batch in records["production_batches"]:
        eligible = [p for p in pkg_lots
                    if p["received_date"] <= batch["production_date"]]
        if eligible:
            pkg_lot = eligible[-1]  # most recent prior lot
            records["batch_packaging_map"].append({
                "batch_id":        batch["batch_id"],
                "packaging_lot_id": pkg_lot["packaging_lot_id"],
            })

    # ---------------------------------------------------------------------------
    # Preset scenarios
    # ---------------------------------------------------------------------------
    # Scenario A: single ingredient lot — chili flakes, limited scope
    # Find a chili flakes lot used in only 1-2 batches
    chili_lots = [r["ingredient_lot_id"] for r in records["ingredient_lots"]
                  if r["ingredient_id"] == "ING-001"]
    # Pick one used in few batches
    chili_usage = {}
    for bim in records["batch_ingredient_map"]:
        if bim["ingredient_lot_id"] in chili_lots:
            chili_usage[bim["ingredient_lot_id"]] = (
                chili_usage.get(bim["ingredient_lot_id"], 0) + 1)
    scenario_a_lot = min(
        (l for l in chili_lots if l in chili_usage),
        key=lambda l: chili_usage.get(l, 0)
    )

    # Scenario B: shared ingredient — pick a chili lot used in many batches across lines
    scenario_b_lot = max(
        (l for l in chili_lots if l in chili_usage),
        key=lambda l: chili_usage.get(l, 0)
    )

    records["scenarios"] = [
        {
            "scenario_id":    "A",
            "title":          "Single Ingredient Lot",
            "description":    "One chili flakes lot touches a single production run — bounded, manageable impact.",
            "root_node_type": "ingredient_lot",
            "root_node_id":   scenario_a_lot,
        },
        {
            "scenario_id":    "B",
            "title":          "Shared Ingredient Across Product Lines",
            "description":    "One chili lot used across multiple SKUs in multiple product lines. "
                              "The gut-punch scenario: blast radius scales non-linearly.",
            "root_node_type": "ingredient_lot",
            "root_node_id":   scenario_b_lot,
        },
        {
            "scenario_id":    "C",
            "title":          "Packaging Lot Spanning Everything",
            "description":    "One label run applied across batches regardless of ingredient. "
                              "Every SKU sharing that label is implicated.",
            "root_node_type": "packaging_lot",
            "root_node_id":   "PKG-LABEL-230110-001",
        },
    ]

    return records


if __name__ == "__main__":
    data = generate_all()
    for table, rows in data.items():
        print(f"{table}: {len(rows)} rows")
