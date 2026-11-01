-- SOLUCIÓN DE REFERENCIA — Tarea 2
-- Una fila por subproducto (nivel 3), con producto (nivel 2) y familia (nivel 1) aplanados.
select
    sub.producto_id                   as producto_id,
    sub.descripcion                   as subproducto,
    prd.producto_id                   as producto_padre_id,
    prd.descripcion                   as producto,
    fam.producto_id                   as familia_id,
    fam.descripcion                   as familia
from {{ ref('productos') }} sub
join {{ ref('productos') }} prd on prd.producto_id = sub.producto_padre_id
join {{ ref('productos') }} fam on fam.producto_id = prd.producto_padre_id
where sub.nivel = 3
