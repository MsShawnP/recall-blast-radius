{{
    config(materialized='table')
}}

/*
  Scope summary per root lot — feeds the scope panel in the UI.
  One row per ingredient_lot_id (the root of a trace-forward).
*/

with nodes as (
    select * from {{ ref('fct_blast_radius') }}
),

fg_lot_scope as (
    select
        br.root_lot_id,
        count(distinct pb.sku_id)       as skus_affected,
        count(distinct br.node_id)      as fg_lots_affected,
        sum(fl.quantity_cases)          as total_cases
    from nodes br
    join {{ ref('stg_fg_lots') }} fl
        on fl.fg_lot_id = br.node_id
    join {{ ref('stg_production_batches') }} pb
        on pb.batch_id = fl.batch_id
    where br.node_type = 'fg_lot'
    group by br.root_lot_id
),

shipment_scope as (
    select
        br.root_lot_id,
        count(distinct br.node_id)      as shipments_affected,
        sum(slm.cases_shipped)          as cases_shipped,
        sum(slm.cases_in_channel)       as cases_in_channel,
        sum(slm.cases_sold_through)     as cases_sold_through
    from nodes br
    -- Join on the full (shipment_id, fg_lot_id) key: a shipment node's parent_id
    -- is its fg_lot_id. Joining on shipment_id alone double-counts shipments that
    -- carry 2+ affected lots and pulls in unaffected lots on mixed shipments.
    join {{ source('genealogy', 'shipment_lot_map') }} slm
        on slm.shipment_id = br.node_id
        and slm.fg_lot_id = br.parent_id
    where br.node_type = 'shipment'
    group by br.root_lot_id
),

retailer_scope as (
    select
        root_lot_id,
        count(distinct node_id)         as retailers_affected,
        array_agg(distinct label)       as notification_list
    from nodes
    where node_type = 'retailer'
    group by root_lot_id
)

select
    coalesce(f.root_lot_id, s.root_lot_id, r.root_lot_id) as root_lot_id,
    coalesce(f.skus_affected, 0)        as skus_affected,
    coalesce(f.fg_lots_affected, 0)     as lots_affected,
    coalesce(f.total_cases, 0)          as total_cases,
    coalesce(s.shipments_affected, 0)   as shipments_affected,
    coalesce(s.cases_shipped, 0)        as cases_shipped,
    coalesce(s.cases_in_channel, 0)     as cases_in_channel,
    coalesce(s.cases_sold_through, 0)   as cases_sold_through,
    coalesce(r.retailers_affected, 0)   as retailers_affected,
    coalesce(r.notification_list, '{}') as notification_list,
    -- Cost model: disposal $4/case + freight $1.50/case + retailer fees $2.50/case + admin $1.00/case
    -- NOTE: the $9.00/$14.00 per-case low/high constants are duplicated in
    -- pipeline/graph.py (packaging_lot_scope) — keep both in sync if they change.
    coalesce(s.cases_in_channel, 0) * 4.00  as disposal_