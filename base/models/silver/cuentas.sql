select
    CTA_ID                                          as cuenta_id,
    CLI_ID                                          as cliente_id,
    PRD_ID                                          as producto_id,
    CTA_MON                                         as moneda,
    CTA_EST                                         as estado,
    strptime(cast(CTA_FEC_ALTA as varchar), '%Y%m%d')::date as fecha_alta
from {{ ref('T_CTA') }}
