select
    SUC_ID                                          as sucursal_id,
    SUC_DESC                                        as descripcion,
    SUC_PROV                                        as provincia
from {{ ref('T_SUC') }}
