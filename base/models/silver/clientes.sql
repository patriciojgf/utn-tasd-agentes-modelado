-- Capa silver: mismos datos que T_CLI, con tipos y nombres legibles.
-- Se conserva el histórico completo (varias filas por cliente).
select
    CLI_ID                                          as cliente_id,
    CLI_NOM                                         as nombre,
    CLI_DOC                                         as documento,
    CLI_COD_SEG                                     as segmento,
    strptime(cast(CLI_FEC_DESDE as varchar), '%Y%m%d')::date as fecha_desde,
    case when CLI_FEC_HASTA = 99991231 then date '9999-12-31'
         else strptime(cast(CLI_FEC_HASTA as varchar), '%Y%m%d')::date
    end                                             as fecha_hasta,
    CLI_SUC                                         as sucursal_id
from {{ ref('T_CLI') }}
