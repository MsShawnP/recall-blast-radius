{{
    config(
        materialized='table',
        indexes=[
            {'columns': ['root_lot_id']},
            {'columns': ['node_type', 'node_id']},
        ]
    )
}}

/*
  Pre-materializes the full blast radius for every ingredient lot and
  packaging lot in the dataset. This powers the API's /trace endpoint
  without running a live recursive CTE per request.

  For a production scale-out: run incrementally, or compute on-demand
  via the FastAPI route (which calls trace_forward.sql directly).
*/

with recursive blast_radius as (

    -- Seed: all ingredient lots
    select
        'ingredient_lot'            as node_type,
        il.ingredient_lot_id        as node_id,
        i.name                      as label,
        il.ingredient_lot_id        as root_lot_id,
        0                           as depth,
        array[il.ingredient_lot_id] as path
    from {{ ref('stg_ingredient_lots') }} il
    join {{ source('genealogy', 'ingredients') }} i using (ingredient_id)

    union all

    -- ingredient_lot → batch
    select
        'batch',
        bim.batch_id,
        pb.co_packer_batch_code,
        br.root_lot_id,
        br.depth + 1,
        br.path || bim.batch_id
    from blast_radius br
    join {{ source('genealogy', 'batch_ingredient_map') }} bim
        on bim.ingredient_lot_id = br.node_id
    join {{ ref('stg_production_batches') }} pb
        on pb.batch_id = bim.batch_id
    where br.node_type = 'ingredient_lot'
      and not bim.batch_id = any(br.path)

    union all

    -- batch → fg_lot
    select
        'fg_lot',
        fl.fg_lot_id,
        fl.internal_lot_code,
        br.root_lot_id,
        br.depth + 1,
        br.path || fl.fg_lot_id
    from blast_radius br
    join {{ ref('stg_fg_lots') }} fl
        on fl.batch_id = br.node_id
    where br.node_type = 'batch'
      and not fl.fg_lot_id = any(br.path)

    union all

    -- fg_lot → shipment
    select
        'shipment',
        slm.shipment_id,
        s.ship_date::text,
        br.root_lot_id,
        br.depth + 1,
        br.path || slm.shipment_id
    from blast_radius br
    join {{ source('genealogy', 'shipment_lot_map') }} slm
        on slm.fg_lot_id = br.node_id
    join {{ source('raw', 'shipments') }} s
        on s.shipment_id = slm.shipment_id
    where br.node_type = 'fg_lot'
      and not slm.shipment_id = any(br.path)

    union all

    -- shipment → retailer
    select
        'retailer',
        s.retailer_id,
        r.retailer_name,
        br.root_lot_id,
        br.depth + 1,
        br.path || s.retailer_id
    from blast_radius br
    join {{ source('raw', 'shipments') }} s
        on s.shipment_id = br.node_id
    join {{ source('raw', 'retailers') }} r
        on r.retailer_id = s.retailer_id
    where br.node_type = 'shipment'
      and not s.retailer_id = any(br.path)

)

select
    root_lot_id,
    node_type,
    node_id,
    label,
    depth,
    path
from blast_radius
