{{
    config(
        materialized='table',
        indexes=[
            {'columns': ['root_lot_id']},
            {'columns': ['node_type', 'node_id']},
            {'columns': ['parent_id']},
        ]
    )
}}

/*
  Pre-materializes the full blast radius for every ingredient lot.
  Fixed 5-level DAG: ingredient_lot → batch → fg_lot → shipment → retailer.

  No recursion needed — the supply chain depth is known and bounded.
  parent_id enables NetworkX edge construction in the Dagster graph asset.
*/

with

il_seed as (
    select
        il.ingredient_lot_id        as root_lot_id,
        'ingredient_lot'            as node_type,
        il.ingredient_lot_id        as node_id,
        ing.name                    as label,
        0                           as depth,
        null::text                  as parent_id
    from {{ ref('stg_ingredient_lots') }} il
    join {{ source('genealogy', 'ingredients') }} ing using (ingredient_id)
),

batch_level as (
    select
        il.root_lot_id,
        'batch'                     as node_type,
        bim.batch_id                as node_id,
        pb.co_packer_batch_code     as label,
        1                           as depth,
        il.node_id                  as parent_id
    from il_seed il
    join {{ source('genealogy', 'batch_ingredient_map') }} bim
        on bim.ingredient_lot_id = il.node_id
    join {{ ref('stg_production_batches') }} pb
        on pb.batch_id = bim.batch_id
),

fg_level as (
    select
        b.root_lot_id,
        'fg_lot'                    as node_type,
        fl.fg_lot_id                as node_id,
        fl.internal_lot_code        as label,
        2                           as depth,
        b.node_id                   as parent_id
    from batch_level b
    join {{ ref('stg_fg_lots') }} fl
        on fl.batch_id = b.node_id
),

shipment_level as (
    select
        f.root_lot_id,
        'shipment'                  as node_type,
        slm.shipment_id             as node_id,
        s.ship_date::text           as label,
        3                           as depth,
        f.node_id                   as parent_id
    from fg_level f
    join {{ source('genealogy', 'shipment_lot_map') }} slm
        on slm.fg_lot_id = f.node_id
    join {{ source('raw', 'shipments') }} s
        on s.shipment_id = slm.shipment_id
),

retailer_level as (
    select
        sh.root_lot_id,
        'retailer'                  as node_type,
        r.retailer_id               as node_id,
        r.retailer_name             as label,
        4                           as depth,
        sh.node_id                  as parent_id
    from shipment_level sh
    join {{ source('raw', 'shipments') }} s
        on s.shipment_id = sh.node_id
    join {{ source('raw', 'retailers') }} r
        on r.retailer_id = s.retailer_id
)

select root_lot_id, node_type, node_id, label, depth, parent_id from il_seed
union all
select root_lot_id, node_type, node_id, label, depth, parent_id from batch_level
union all
select root_lot_id, node_type, node_id, label, depth, parent_id from fg_level
union all
select root_lot_id, node_type, node_id, label, depth, parent_id from shipment_level
union all
select root_lot_id, node_type, node_id, label, depth, parent_id from retailer_level
