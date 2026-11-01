#!/usr/bin/env bash
# Corre el agente dentro del contenedor. Solo ve /trabajo (la carpeta de su corrida).
# Los registros (transcript, duración, errores) van a /registro, que el agente no ve.
#
# Uso (lo llama tasd.sh):  tasd-agente auto         -> sin intervención, para las 20 corridas
#                          tasd-agente interactivo  -> sesión en vivo, para la demo
set -u
MODO="${1:-auto}"
: "${MODELO:?Falta MODELO en el archivo .env}"

PROMPT="Leé TAREA.md y resolvé la tarea siguiendo las instrucciones de CLAUDE.md."
# Mismos permisos en los dos modos: leer y escribir archivos de la carpeta, correr dbt y
# consultar la base. Cualquier otro comando se rechaza.
HERRAMIENTAS=("Read" "Write" "Edit" "Glob" "Grep" "Bash(dbt *)" "Bash(python -c *)" "Bash(ls *)")
# Sin acceso a internet: todo lo que sabe el agente sale de la carpeta.
PROHIBIDAS=("WebFetch" "WebSearch")

cd /trabajo

if [[ "$MODO" == "interactivo" ]]; then
  echo "Mensaje para pegar:  $PROMPT"
  echo
  exec claude --model "$MODELO" --permission-mode acceptEdits --allowedTools "${HERRAMIENTAS[@]}" \
    --disallowedTools "${PROHIBIDAS[@]}"
fi

REG=/registro
INICIO=$(date +%s)
claude -p "$PROMPT" \
  --model "$MODELO" \
  --output-format stream-json --verbose \
  --permission-mode acceptEdits \
  --allowedTools "${HERRAMIENTAS[@]}" \
  --disallowedTools "${PROHIBIDAS[@]}" \
  > "$REG/transcript.jsonl" 2> "$REG/errores_agente.txt"
CODIGO=$?
echo "codigo de salida del agente: $CODIGO" >> "$REG/errores_agente.txt"
echo $(( $(date +%s) - INICIO )) > "$REG/duracion_segundos.txt"
echo "$MODELO" > "$REG/modelo.txt"
claude --version > "$REG/version_claude.txt" 2>&1
exit $CODIGO
