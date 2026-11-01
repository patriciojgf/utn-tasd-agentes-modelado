select
    strptime(cast(TC_FEC as varchar), '%Y%m%d')::date as fecha,
    TC_MON                                          as moneda,
    TC_VAL                                          as valor
from {{ ref('T_TIPCAMB') }}
