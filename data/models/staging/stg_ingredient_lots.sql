select
    ingredient_lot_id,
    ingredient_id,
    co_packer_id,
    supplier_name,
    supplier_lot_code,
    co_packer_lot_code,
    quantity_lbs::numeric          as quantity_lbs,
    received_date::date            as received_date,
    best_by_date::date             as best_by_date,
    status
from {{ source('genealogy', 'ingredient_lots') }}
