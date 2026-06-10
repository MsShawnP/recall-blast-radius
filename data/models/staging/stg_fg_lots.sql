select
    fg_lot_id,
    batch_id,
    sku_id,
    internal_lot_code,
    co_packer_lot_code,
    quantity_cases::integer        as quantity_cases,
    production_date::date          as production_date,
    best_by_date::date             as best_by_date,
    status
from {{ source('genealogy', 'fg_lots') }}
