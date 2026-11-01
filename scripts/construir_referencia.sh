#!/usr/bin/env bash
# Construye la base de datos de referencia (la "respuesta correcta").
# Copia el proyecto base, le agrega los modelos gold de referencia y corre dbt.
# Resultado: referencia/proyecto/banco.duckdb
set -e
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$RAIZ/referencia/proyecto"

rm -rf "$DEST"
cp -r "$RAIZ/base" "$DEST"
rm -rf "$DEST/target" "$DEST/logs" "$DEST/banco.duckdb"
cp "$RAIZ/referencia/models/gold/"* "$DEST/models/gold/"
# La referencia usa la versión documentada del silver (no afecta los datos, solo la doc).
cp "$RAIZ/metadatos/models/silver/schema.yml" "$DEST/models/silver/schema.yml"

cd "$DEST"
dbt seed --profiles-dir . --quiet
dbt run  --profiles-dir . --quiet
dbt test --profiles-dir . --quiet
echo
echo "Referencia construida en: $DEST/banco.duckdb"
