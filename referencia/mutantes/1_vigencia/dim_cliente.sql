-- MUTANTE 1: sin filtro de vigencia
select
    c.cliente_id,
    c.nombre,
    c.documento,
    c.segmento,
    c.fecha_desde                     as segmento_desde,
    c.sucursal_id,
    s.descripcion                     as sucursal,
    s.provincia
from {{ ref('clientes') }} c
left join {{ ref('sucursales') }} s on s.sucursal_id = c.sucursal_id
