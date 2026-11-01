select
    MOV_ID                                          as movimiento_id,
    CTA_ID                                          as cuenta_id,
    strptime(cast(MOV_FEC as varchar), '%Y%m%d')::date as fecha,
    MOV_TIP                                         as tipo,
    MOV_IMP_ORI                                     as importe_original,
    MOV_MON                                         as moneda
from {{ ref('T_MOV') }}
