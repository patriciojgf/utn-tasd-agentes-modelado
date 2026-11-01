select
    PRD_ID                                          as producto_id,
    PRD_DESC                                        as descripcion,
    PRD_PADRE                                       as producto_padre_id,
    PRD_NIV                                         as nivel
from {{ ref('T_PRD') }}
