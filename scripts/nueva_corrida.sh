#!/usr/bin/env bash
# Crea una carpeta de corrida lista para que trabaje el agente.
# Normalmente no se llama a mano: lo usa ./tasd.sh (preparar, correr, todas, demo).
#
# Uso:  bash scripts/nueva_corrida.sh <condicion> <tarea> <repeticion>
#   condicion : sin | con        (sin metadatos / con metadatos)
#   tarea     : T1 (modelo) | T2 (tests) | T3 (documentación)
#   repeticion: 1 | 2 | 3 ...
#
# Ejemplo: bash scripts/nueva_corrida.sh con T3 1
#   -> crea corridas/con_metadatos/T3_rep1/
set -e
COND="$1"; TAREA="$2"; REP="$3"
if [[ -z "$COND" || -z "$TAREA" || -z "$REP" ]]; then
  echo "Uso: bash scripts/nueva_corrida.sh <sin|con> <T1..T3> <repeticion>"; exit 1
fi
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

case "$COND" in
  sin) CARPETA="sin_metadatos" ;;
  con) CARPETA="con_metadatos" ;;
  *) echo "condicion debe ser 'sin' o 'con'"; exit 1 ;;
esac

# El agente corre en un contenedor que solo monta esta carpeta: no ve los scripts,
# la referencia ni los metadatos. Se puede cambiar la ubicación con CORRIDAS_DIR.
DEST="${CORRIDAS_DIR:-$RAIZ/corridas}/$CARPETA/${TAREA}_rep${REP}"
if [[ -d "$DEST" ]]; then echo "Ya existe: $DEST"; exit 1; fi
mkdir -p "$(dirname "$DEST")"

# 1. Copia limpia del proyecto base
cp -r "$RAIZ/base" "$DEST"
rm -rf "$DEST/target" "$DEST/logs" "$DEST/banco.duckdb"

# 2. Si la condición es "con", agrega los metadatos
if [[ "$COND" == "con" ]]; then
  cp "$RAIZ/metadatos/models/silver/schema.yml" "$DEST/models/silver/schema.yml"
  mkdir -p "$DEST/docs"
  cp "$RAIZ/metadatos/docs/reglas_negocio.md" "$DEST/docs/"
  cp "$RAIZ/metadatos/docs/modelo_gold.md" "$DEST/docs/"
fi

# 3. Consigna de la tarea e instrucciones para el agente
cp "$RAIZ/tareas/${TAREA}.md" "$DEST/TAREA.md"
# Agente según la etapa (mismas instrucciones en los dos escenarios)
case "$TAREA" in
  T1)       AGENTE="modelador" ;;
  T2)       AGENTE="tester" ;;
  T3)       AGENTE="documentador" ;;
  *) echo "tarea debe ser T1..T3"; exit 1 ;;
esac
cp "$RAIZ/tareas/agentes/${AGENTE}.md" "$DEST/CLAUDE.md"

# 3b. Las tareas T2 (tests) y T3 (documentación) trabajan SOBRE modelos gold ya hechos:
#     se copian los SQL de referencia (sin su schema.yml, que es lo que el agente debe producir).
if [[ "$TAREA" == "T2" || "$TAREA" == "T3" ]]; then
  for m in dim_cliente dim_producto dim_cuenta fact_movimientos; do
    cp "$RAIZ/referencia/models/gold/$m.sql" "$DEST/models/gold/"
  done
  cat > "$DEST/models/gold/schema.yml" <<'YML'
version: 2
models:
  - name: dim_cliente
  - name: dim_producto
  - name: dim_cuenta
  - name: fact_movimientos
YML
fi

# 4. Carga bronze + silver para que el agente arranque con la base lista
cd "$DEST"
dbt seed --profiles-dir . --quiet
if [[ "$TAREA" == "T2" || "$TAREA" == "T3" ]]; then
  dbt run --profiles-dir . --quiet
else
  dbt run --profiles-dir . --quiet --select silver
fi

rm -rf "$DEST/logs"
echo "Corrida creada: $DEST"
