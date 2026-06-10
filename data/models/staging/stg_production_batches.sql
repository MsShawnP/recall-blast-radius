select
    batch_id,
    sku_id,
    co_packer_id,
    production_date::date          as production_date,
    batch_quantity_cases::integer  as batch_quantity_cases,
    co_packer_batch_code,
    status
from {{ source('genealogy', 'production_batches') }}
