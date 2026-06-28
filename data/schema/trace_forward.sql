-- Trace-forward recursive CTE: ingredient lot → blast radius
-- Usage: replace :lot_id with an ingredient_lot_id or packaging_lot_id

WITH RECURSIVE blast_radius AS (

    -- Base case: the contaminated ingredient lot
    SELECT
        'ingredient_lot'                AS node_type,
        il.ingredient_lot_id            AS node_id,
        i.name                          AS label,
        il.ingredient_lot_id            AS root_id,
        0                               AS depth,
        ARRAY[il.ingredient_lot_id]     AS path
    FROM genealogy.ingredient_lots il
    JOIN genealogy.ingredients i USING (ingredient_id)
    WHERE il.ingredient_lot_id = :lot_id

    UNION ALL

    -- ingredient_lot → production_batches
    SELECT
        'batch'                         AS node_type,
        pb.batch_id                     AS node_id,
        pb.co_packer_batch_code         AS label,
        br.root_id,
        br.depth + 1                    AS depth,
        br.path || pb.batch_id          AS path
    FROM blast_radius br
    JOIN genealogy.batch_ingredient_map bim ON bim.ingredient_lot_id = br.node_id
    JOIN genealogy.production_batches pb ON pb.batch_id = bim.batch_id
    WHERE br.node_type = 'ingredient_lot'
      AND NOT pb.batch_id = ANY(br.path)

    UNION ALL

    -- production_batch → fg_lots
    SELECT
        'fg_lot'                        AS node_type,
        fl.fg_lot_id                    AS node_id,
        fl.internal_lot_code            AS label,
        br.root_id,
        br.depth + 1                    AS depth,
        br.path || fl.fg_lot_id         AS path
    FROM blast_radius br
    JOIN genealogy.fg_lots fl ON fl.batch_id = br.node_id
    WHERE br.node_type = 'batch'
      AND NOT fl.fg_lot_id = ANY(br.path)

    UNION ALL

    -- fg_lot → shipments
    SELECT
        'shipment'                      AS node_type,
        slm.shipment_id                 AS node_id,
        s.ship_date::TEXT               AS label,
        br.root_id,
        br.depth + 1                    AS depth,
        br.path || slm.shipment_id      AS path
    FROM blast_radius br
    JOIN genealogy.shipment_lot_map slm ON slm.fg_lot_id = br.node_id
    JOIN raw.shipments s ON s.shipment_id = slm.shipment_id
    WHERE br.node_type = 'fg_lot'
      AND NOT slm.shipment_id = ANY(br.path)

    UNION ALL

    -- shipment → retailers
    SELECT
        'retailer'                      AS node_type,
        s.retailer_id                   AS node_id,
        r.name                          AS label,
        br.root_id,
        br.depth + 1                    AS depth,
        br.path || s.retailer_id        AS path
    FROM blast_radius br
    JOIN raw.shipments s ON s.shipment_id = br.node_id
    JOIN raw.retailers r ON r.retailer_id = s.retailer_id
    WHERE br.node_type = 'shipment'
      AND NOT s.retailer_id = ANY(br.path)
)

SELECT
    node_type,
    node_id,
    label,
    depth,
    path
FROM blast_radius
ORDER BY depth, node_type, node_id;


-- Scope summary query (run after blast_radius CTE to get the scope panel)
-- SELECT
--     COUNT(DISTINCT CASE WHEN node_type = 'fg_lot' THEN node_id END)   AS lots_affected,
--     COUNT(DISTINCT CASE WHEN node_type = 'shipment' THEN node_id END) AS shipments_affected,
--     COUNT(DISTINCT CASE WHEN node_type = 'retailer' THEN node_id END) AS retailers_affected,
--     SUM(CASE WHEN node_type = 'fg_lot'
--         THEN (SELECT quantity_cases FROM genealogy.fg_lots WHERE fg_lot_id = br.node_id)
--         ELSE 0 END)                                                    AS total_cases
-- FROM blast_radius br;
