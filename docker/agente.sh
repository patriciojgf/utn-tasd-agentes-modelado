#!/usr/bin/env bash
# Corre el agente dentro del contenedor. Solo ve /trabajo (la carpeta de su corrida).
# Los registros (transcript, duración, errores) van a /registro, que el agente no ve.
#
# Uso (lo llama tasd.sh):  tasd-agente auto         -> sin intervención
#                          tasd-agente interactivo  -> sesión en la que le escribís vos
#
# AGENTE elige la herramienta: "claude" (Claude Code, la del experimento original) o
# "gemini" (Gemini CLI). Las dos leen las mismas instrucciones (CLAUDE.md y TAREA.md) y
# tienen los mismos permisos: leer y escribir archivos de la carpeta, correr dbt y
# consultar la base, sin internet.
set -u
MODO="${1:-auto}"
AGENTE="${AGENTE:-claude}"
: "${MODELO:?Falta MODELO en el archivo .env}"

PROMPT="Leé TAREA.md y resolvé la tarea siguiendo las instrucciones de CLAUDE.md."
REG=/registro

cd /trabajo

# ---------------------------------------------------------------- Claude Code
if [[ "$AGENTE" == "claude" ]]; then
  HERRAMIENTAS=("Read" "Write" "Edit" "Glob" "Grep" "Bash(dbt *)" "Bash(python -c *)" "Bash(ls *)")
  PROHIBIDAS=("WebFetch" "WebSearch")

  if [[ "$MODO" == "interactivo" ]]; then
    echo "Mensaje para pegar:  $PROMPT"
    echo
    exec claude --model "$MODELO" --permission-mode acceptEdits --allowedTools "${HERRAMIENTAS[@]}" \
      --disallowedTools "${PROHIBIDAS[@]}"
  fi

  INICIO=$(date +%s)
  claude -p "$PROMPT" \
    --model "$MODELO" \
    --output-format stream-json --verbose \
    --permission-mode acceptEdits \
    --allowedTools "${HERRAMIENTAS[@]}" \
    --disallowedTools "${PROHIBIDAS[@]}" \
    > "$REG/transcript.jsonl" 2> "$REG/errores_agente.txt"
  CODIGO=$?
  claude --version > "$REG/version_agente.txt" 2>&1

# ---------------------------------------------------------------- Gemini CLI
elif [[ "$AGENTE" == "gemini" ]]; then
  # Las herramientas permitidas y el archivo de instrucciones (CLAUDE.md) están fijados en
  # /etc/gemini-cli/settings.json, que el agente no puede modificar.
  if [[ "$MODO" == "interactivo" ]]; then
    echo "Mensaje para pegar:  $PROMPT"
    echo
    exec gemini --model "$MODELO" --approval-mode auto_edit
  fi

  INICIO=$(date +%s)
  # yolo aprueba sin preguntar, pero solo las herramientas de la lista de settings.json.
  gemini --model "$MODELO" --prompt "$PROMPT" \
    --approval-mode yolo \
    --output-format stream-json \
    > "$REG/transcript.jsonl" 2> "$REG/errores_agente.txt"
  CODIGO=$?
  gemini --version > "$REG/version_agente.txt" 2>&1

else
  echo "AGENTE tiene que ser 'claude' o 'gemini' (vale '$AGENTE')" >&2
  exit 2
fi

echo "codigo de salida del agente: $CODIGO" >> "$REG/errores_agente.txt"
echo $(( $(date +%s) - INICIO )) > "$REG/duracion_segundos.txt"
echo "$AGENTE $MODELO" > "$REG/modelo.txt"
exit $CODIGO
