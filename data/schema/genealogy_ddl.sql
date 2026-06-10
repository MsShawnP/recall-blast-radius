-- Recall Blast Radius — Lot Genealogy Schema
-- Extends the Cinderhaven platform with a new dimension.
-- Standalone Postgres; references canonical SKU/retailer IDs but does not
-- require a live connection to cinderhaven-data-platform.

-- Platform stubs (minimal; seeded from canonical values)
CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.product_master (
    sku_id          TEXT PRIMARY KEY,
    sku_name        TEXT NOT NULL,
    product_line    TEXT NOT NULL,    -- AS / PS / SC / DG / SB
    cases_per_pallet INTEGER NOT NULL DEFAULT 60
);

CREATE TABLE IF NOT EXISTS raw.retailers (
    retailer_id     TEXT PRIMARY KEY,
    retailer_name   TEXT NOT NULL,
    store_doors     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS raw.shipments (
    shipment_id     TEXT PRIMARY KEY,
    order_id        TEXT NOT NULL,
    retailer_id     TEXT REFERENCES raw.retailers(retailer_id),
    ship_date       DATE NOT NULL,
    cases_shipped   INTEGER NOT NULL
);

-- ---------------------------------------------------------------------------
-- New genealogy dimension
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS genealogy;

-- Co-packers who manufacture for Cinderhaven.
-- Lot-code format varies per co-packer — this is the real-world complexity.
CREATE TABLE genealogy.co_packers (
    co_packer_id        TEXT PRIMARY KEY,           -- e.g. CP-EAST
    name                TEXT NOT NULL,
    lot_code_format     TEXT NOT NULL,              -- julian_line | sequential_date | yearweek_seq
    primary_lines       TEXT[] NOT NULL             -- product lines they produce
);

-- Raw material / ingredient catalog.
CREATE TABLE genealogy.ingredients (
    ingredient_id       TEXT PRIMARY KEY,           -- e.g. ING-001
    name                TEXT NOT NULL,              -- e.g. "Chili Flakes"
    category            TEXT NOT NULL,              -- spice / sauce_base / sweetener / acid / packaging
    unit                TEXT NOT NULL DEFAULT 'lbs',
    is_ftl_upstream     BOOLEAN NOT NULL DEFAULT FALSE
    -- TRUE when this ingredient's own supply chain involves FTL-covered
    -- commodities (e.g., fresh peppers → hot sauce). The finished SKU
    -- may not be FTL-covered, but the upstream step is.
);

-- Specific lots of ingredients received at the co-packer.
-- This is the blast-radius root node in Scenario A and B.
CREATE TABLE genealogy.ingredient_lots (
    ingredient_lot_id   TEXT PRIMARY KEY,           -- e.g. ING-001-240312-A
    ingredient_id       TEXT NOT NULL REFERENCES genealogy.ingredients(ingredient_id),
    co_packer_id        TEXT NOT NULL REFERENCES genealogy.co_packers(co_packer_id),
    supplier_name       TEXT NOT NULL,
    supplier_lot_code   TEXT,                       -- supplier's own code (optional)
    co_packer_lot_code  TEXT NOT NULL,              -- co-packer's internal receipt code
    quantity_lbs        NUMERIC(10,2) NOT NULL,
    received_date       DATE NOT NULL,
    best_by_date        DATE,
    status              TEXT NOT NULL DEFAULT 'consumed'
    -- active | consumed | recalled | quarantine
);

-- Production batches: one run at the co-packer producing a single SKU.
CREATE TABLE genealogy.production_batches (
    batch_id            TEXT PRIMARY KEY,           -- e.g. BTH-CP01-240312-01
    sku_id              TEXT NOT NULL REFERENCES raw.product_master(sku_id),
    co_packer_id        TEXT NOT NULL REFERENCES genealogy.co_packers(co_packer_id),
    production_date     DATE NOT NULL,
    batch_quantity_cases INTEGER NOT NULL,
    co_packer_batch_code TEXT NOT NULL,             -- co-packer's batch identifier
    status              TEXT NOT NULL DEFAULT 'shipped'
    -- in_production | qc_hold | shipped | recalled
);

-- Which ingredient lots went into which batch.
-- This is the core graph edge for trace-forward traversal.
CREATE TABLE genealogy.batch_ingredient_map (
    batch_id            TEXT NOT NULL REFERENCES genealogy.production_batches(batch_id),
    ingredient_lot_id   TEXT NOT NULL REFERENCES genealogy.ingredient_lots(ingredient_lot_id),
    quantity_used_lbs   NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (batch_id, ingredient_lot_id)
);

-- Finished-goods lots: what gets labeled and enters Cinderhaven's inventory.
-- Note: co_packer_lot_code ≠ internal_lot_code — lot codes mutate at repack.
-- This is one of the real-world traps: 3PL logs use one code; Cinderhaven
-- uses another; the mapping layer is the engagement.
CREATE TABLE genealogy.fg_lots (
    fg_lot_id           TEXT PRIMARY KEY,           -- e.g. FGL-CHP-AS-001-240312-001
    batch_id            TEXT NOT NULL REFERENCES genealogy.production_batches(batch_id),
    sku_id              TEXT NOT NULL REFERENCES raw.product_master(sku_id),
    internal_lot_code   TEXT NOT NULL,              -- Cinderhaven's code (ERP)
    co_packer_lot_code  TEXT NOT NULL,              -- co-packer's code for same lot
    quantity_cases      INTEGER NOT NULL,
    production_date     DATE NOT NULL,
    best_by_date        DATE NOT NULL,
    status              TEXT NOT NULL DEFAULT 'sold_through'
    -- in_warehouse | in_channel | sold_through | recalled | disposed
);

-- Packaging lots: a run of labels/film/packaging material.
-- Scenario C root node — one packaging lot can span many batches/SKUs.
CREATE TABLE genealogy.packaging_lots (
    packaging_lot_id    TEXT PRIMARY KEY,           -- e.g. PKG-LABEL-240110-001
    packaging_type      TEXT NOT NULL,              -- label | film | carton | corrugated
    supplier_name       TEXT NOT NULL,
    lot_code            TEXT NOT NULL,
    quantity_units      INTEGER NOT NULL,
    received_date       DATE NOT NULL
);

-- Which packaging lot was used in which batch.
CREATE TABLE genealogy.batch_packaging_map (
    batch_id            TEXT NOT NULL REFERENCES genealogy.production_batches(batch_id),
    packaging_lot_id    TEXT NOT NULL REFERENCES genealogy.packaging_lots(packaging_lot_id),
    PRIMARY KEY (batch_id, packaging_lot_id)
);

-- Which FG lots are in which shipment (links genealogy to existing platform).
CREATE TABLE genealogy.shipment_lot_map (
    shipment_id         TEXT NOT NULL REFERENCES raw.shipments(shipment_id),
    fg_lot_id           TEXT NOT NULL REFERENCES genealogy.fg_lots(fg_lot_id),
    cases_shipped       INTEGER NOT NULL,
    cases_in_channel    INTEGER,                    -- estimated remaining at trace time
    cases_sold_through  INTEGER,                    -- estimated sold
    PRIMARY KEY (shipment_id, fg_lot_id)
);

-- ---------------------------------------------------------------------------
-- Preset scenario markers
-- ---------------------------------------------------------------------------

CREATE TABLE genealogy.scenarios (
    scenario_id         TEXT PRIMARY KEY,           -- A | B | C
    title               TEXT NOT NULL,
    description         TEXT NOT NULL,
    root_node_type      TEXT NOT NULL,              -- ingredient_lot | packaging_lot
    root_node_id        TEXT NOT NULL               -- the lot_id to start the trace from
);

-- ---------------------------------------------------------------------------
-- Indexes for recursive CTE performance
-- ---------------------------------------------------------------------------

CREATE INDEX idx_bim_ingredient_lot ON genealogy.batch_ingredient_map(ingredient_lot_id);
CREATE INDEX idx_bim_batch ON genealogy.batch_ingredient_map(batch_id);
CREATE INDEX idx_fglots_batch ON genealogy.fg_lots(batch_id);
CREATE INDEX idx_slm_fg_lot ON genealogy.shipment_lot_map(fg_lot_id);
CREATE INDEX idx_slm_shipment ON genealogy.shipment_lot_map(shipment_id);
CREATE INDEX idx_bpm_packaging_lot ON genealogy.batch_packaging_map(packaging_lot_id);
CREATE INDEX idx_ingredient_lots_ingredient ON genealogy.ingredient_lots(ingredient_id);
