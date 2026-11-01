#!/usr/bin/env bash
# Punto de entrada único del experimento. Todo corre en Docker; en la Mac solo hace falta
# Docker Desktop. Ejecutar sin argumentos para ver la ayuda.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")" && pwd)"
IMAGEN="tasd-tp:1"
CORRIDAS="$RAIZ/corridas"
DEMO="$RAIZ/demo"
TTY=(); [[ -t 0 && -t 1 ]] && TTY=(-it)

# Orden de las corridas: alterna escenarios y tareas (paso 10 de la guía).
ORDEN=("T1" "T2" "T3")

ayuda() {
  cat <<'EOF'
Uso: ./tasd.sh <comando> [argumentos]

Preparación (una sola vez)
  construir                     Construye la imagen de Docker
  datos                         Regenera los CSV con scripts/generar_datos.py (opcional)
  referencia                    Construye la solución de referencia
  autotest                      Verifica el evaluador con resultados simulados (no usa el agente)
  humo                          Arma una corrida "sin" y una "con" de T1 y muestra qué ve el agente

Experimento
  correr <sin|con> <T1..T3> <rep>   Una corrida: prepara, corre el agente sin intervención y evalúa
  abrir <sin|con> <T1..T3> <rep>    Una corrida interactiva: le escribís vos la tarea al agente; al salir se evalúa
  todas [reps...]                   Las 12 corridas (por defecto reps 1 y 2), salteando las hechas
  estado                            Qué corridas están hechas, incompletas o pendientes
  preparar <sin|con> <T> <rep>      Solo arma la carpeta de la corrida (sin agente)
  evaluar <sin|con> <T> <rep>       Vuelve a evaluar una corrida

Resultados
  revision                      Prepara la revisión manual: diseño de T1 y documentación de T3 (a ciegas)
  consolidar                    Junta todo: CSV + resultados/reporte.md + resultados/reporte.html

Demo en clase
  demo <sin|con>                Sesión interactiva del agente sobre T1 (abrir una terminal por escenario)
  demo-comparar                 Evalúa las dos sesiones de la demo y las muestra lado a lado

Otros
  shell                         Terminal dentro del contenedor, con el proyecto montado
EOF
}

# ---------------------------------------------------------------- utilidades
error() { echo "Error: $*" >&2; exit 1; }

verificar_docker() {
  docker info >/dev/null 2>&1 || error "Docker no está corriendo. Abrí Docker Desktop y probá de nuevo."
}

verificar_imagen() {
  verificar_docker
  docker image inspect "$IMAGEN" >/dev/null 2>&1 || error "Falta la imagen. Corré: ./tasd.sh construir"
}

verificar_ubicacion() {
  # DuckDB escribe todo el tiempo en su archivo; dentro de Google Drive la sincronización
  # puede trabarlo o generar conflictos.
  if [[ "$RAIZ" == */Library/CloudStorage/* && -z "${TASD_EN_DRIVE:-}" ]]; then
    echo "Atención: el proyecto está dentro de Google Drive. Conviene copiarlo a una carpeta local:"
    echo "  cp -R \"$RAIZ\" ~/tasd-docker && cd ~/tasd-docker"
    if [[ -t 0 ]]; then
      read -r -p "¿Seguir igual acá? [s/N] " r
      [[ "$r" == "s" || "$r" == "S" ]] || exit 1
      export TASD_EN_DRIVE=1
    else
      exit 1
    fi
  fi
}

verificar_env() {
  [[ -f "$RAIZ/.env" ]] || error "Falta el archivo .env. Copiá .env.example como .env y completalo."
  # shellcheck disable=SC1091
  ( set -a; source "$RAIZ/.env"
    [[ -n "${MODELO:-}" ]] || { echo "Error: falta MODELO en .env" >&2; exit 1; }
    case "${AGENTE:-claude}" in
      claude)
        [[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}${ANTHROPIC_API_KEY:-}" ]] || \
          { echo "Error: falta CLAUDE_CODE_OAUTH_TOKEN o ANTHROPIC_API_KEY en .env" >&2; exit 1; } ;;
      gemini)
        [[ -n "${GEMINI_API_KEY:-}" ]] || \
          { echo "Error: falta GEMINI_API_KEY en .env (se saca en https://aistudio.google.com/apikey)" >&2; exit 1; } ;;
      *) echo "Error: AGENTE en .env tiene que ser claude o gemini" >&2; exit 1 ;;
    esac )
}

verificar_referencia() {
  [[ -f "$RAIZ/referencia/proyecto/banco.duckdb" ]] || error "Falta la referencia. Corré: ./tasd.sh referencia"
}

condicion() {
  case "${1:-}" in
    sin) echo "sin_metadatos" ;;
    con) echo "con_metadatos" ;;
    *) error "el escenario tiene que ser 'sin' o 'con'" ;;
  esac
}

validar_tarea() { [[ "${1:-}" =~ ^T[1-3]$ ]] || error "la tarea tiene que ser T1 (modelo), T2 (tests) o T3 (documentación)"; }
validar_rep()   { [[ "${1:-}" =~ ^[0-9]+$ ]] || error "la repetición tiene que ser un número"; }

# Contenedor con el proyecto montado: preparar, evaluar, consolidar.
en_proyecto() {
  docker run --rm ${TTY[@]+"${TTY[@]}"} -v "$RAIZ:/proyecto" -w /proyecto \
    -e CORRIDAS_DIR="${CORRIDAS_DIR_CONT:-/proyecto/corridas}" "$IMAGEN" "$@"
}

# Contenedor del agente: SOLO ve la carpeta de su corrida (en /trabajo).
en_agente() {
  local corrida="$1" registro="$2" modo="$3"
  local montajes=(-v "$corrida:/trabajo") variables=()
  [[ -n "$registro" ]] && montajes+=(-v "$registro:/registro")
  set -a; source "$RAIZ/.env"; set +a
  if [[ "${AGENTE:-claude}" == "gemini" ]]; then
    # Cada corrida tiene su propia carpeta de Gemini (sesión e historial), así una corrida
    # no ve lo que pasó en otra. La autenticación es con GEMINI_API_KEY.
    local casa="${registro:-$(mktemp -d)}/sesion_gemini"
    mkdir -p "$casa"
    montajes+=(-v "$casa:/home/agente/.gemini")
  elif [[ "$modo" == "interactivo" && -n "$registro" ]]; then
    # En modo interactivo se guarda la sesión de Claude Code para tener el transcript.
    mkdir -p "$registro/sesion"
    montajes+=(-v "$registro/sesion:/home/agente/.claude")
  fi
  # Se pasan solo las variables con valor, por nombre (el token no queda en la línea de comandos).
  for v in AGENTE MODELO CLAUDE_CODE_OAUTH_TOKEN ANTHROPIC_API_KEY GEMINI_API_KEY; do
    [[ -n "${!v:-}" ]] && variables+=(-e "$v")
  done
  docker run --rm ${TTY[@]+"${TTY[@]}"} ${variables[@]+"${variables[@]}"} "${montajes[@]}" -w /trabajo \
    "$IMAGEN" tasd-agente "$modo"
}

# ---------------------------------------------------------------- comandos
cmd_construir() {
  verificar_docker
  docker build -t "$IMAGEN" "$RAIZ"
  echo
  docker run --rm "$IMAGEN" bash -c 'python --version; dbt --version | grep -E "installed|duckdb"; \
    python -c "import duckdb; print(\"DuckDB\", duckdb.__version__)"; claude --version; \
    echo "Gemini CLI $(gemini --version)"'
}

cmd_datos() {
  verificar_imagen; verificar_ubicacion
  en_proyecto python scripts/generar_datos.py
  echo "Si cambiaron los datos, corré de nuevo: ./tasd.sh referencia"
}

cmd_referencia() {
  verificar_imagen; verificar_ubicacion
  en_proyecto bash scripts/construir_referencia.sh
  en_proyecto python -c "
import duckdb
c = duckdb.connect('referencia/proyecto/banco.duckdb', read_only=True)
print('Números de la referencia (para la Tabla 2 del informe):')
print('  clientes en dim_cliente   ', c.sql('select count(*) from gold.dim_cliente').fetchone()[0])
print('  filas en silver.clientes  ', c.sql('select count(*) from silver.clientes').fetchone()[0])
print('  movimientos válidos       ', c.sql('select count(*) from gold.fact_movimientos').fetchone()[0])
print('  movimientos totales       ', c.sql('select count(*) from silver.movimientos').fetchone()[0])
print('  suma en pesos             ', c.sql('select round(sum(importe_pesos), 2) from gold.fact_movimientos').fetchone()[0])
print('  subproductos en dim       ', c.sql('select count(*) from gold.dim_producto').fetchone()[0])
print('  filas en silver.productos ', c.sql('select count(*) from silver.productos').fetchone()[0])
"
}

cmd_autotest() {
  verificar_imagen; verificar_ubicacion; verificar_referencia
  en_proyecto python scripts/autotest.py
}

cmd_humo() {
  verificar_imagen; verificar_ubicacion
  local tmp="$RAIZ/.humo"; rm -rf "$tmp"
  CORRIDAS_DIR_CONT=/proyecto/.humo en_proyecto bash scripts/nueva_corrida.sh sin T1 1 >/dev/null
  CORRIDAS_DIR_CONT=/proyecto/.humo en_proyecto bash scripts/nueva_corrida.sh con T1 1 >/dev/null
  for c in sin con; do
    echo "== Lo que ve el agente en el escenario '$c' (/trabajo):"
    docker run --rm -v "$tmp/${c}_metadatos/T1_rep1:/trabajo" -w /trabajo "$IMAGEN" \
      bash -c 'ls -p; [ -d docs ] && echo "  docs/: $(ls docs)"; echo "  CLAUDE.md: $(head -1 CLAUDE.md)"'
  done
  echo "== ¿El agente puede ver la referencia?"
  docker run --rm -v "$tmp/sin_metadatos/T1_rep1:/trabajo" -w /trabajo "$IMAGEN" \
    bash -c 'ls /proyecto 2>/dev/null && echo "  SÍ: hay un problema" || echo "  No: /proyecto no existe dentro del contenedor del agente."'
  rm -rf "$tmp"
}

cmd_preparar() {
  local cond; cond="$(condicion "${1:-}")"; validar_tarea "${2:-}"; validar_rep "${3:-}"
  verificar_imagen; verificar_ubicacion
  en_proyecto bash scripts/nueva_corrida.sh "$1" "$2" "$3"
}

cmd_evaluar() {
  local cond; cond="$(condicion "${1:-}")"; validar_tarea "${2:-}"; validar_rep "${3:-}"
  verificar_imagen; verificar_referencia
  [[ -d "$CORRIDAS/$cond/${2}_rep${3}" ]] || error "no existe la corrida $cond/${2}_rep${3}"
  en_proyecto python scripts/evaluar.py "corridas/$cond/${2}_rep${3}"
}

cmd_correr() {
  local cond; cond="$(condicion "${1:-}")"; validar_tarea "${2:-}"; validar_rep "${3:-}"
  verificar_imagen; verificar_ubicacion; verificar_env; verificar_referencia
  local nombre="${2}_rep${3}"
  local corrida="$CORRIDAS/$cond/$nombre" registro="$CORRIDAS/_registros/$cond/$nombre"
  [[ -e "$corrida" ]] && error "ya existe $cond/$nombre. Si se cortó, repetila con otro número y anotalo."
  echo "==> [$cond / $nombre] preparando la carpeta"
  en_proyecto bash scripts/nueva_corrida.sh "$1" "$2" "$3"
  mkdir -p "$registro"
  echo "==> [$cond / $nombre] trabajando el agente (sin intervención)..."
  local codigo=0
  en_agente "$corrida" "$registro" auto || codigo=$?
  [[ $codigo -ne 0 ]] && echo "    El agente terminó con código $codigo (ver $registro/errores_agente.txt)"
  echo "==> [$cond / $nombre] evaluando"
  en_proyecto python scripts/evaluar.py "corridas/$cond/$nombre"
}

cmd_abrir() {
  local cond; cond="$(condicion "${1:-}")"; validar_tarea "${2:-}"; validar_rep "${3:-}"
  verificar_imagen; verificar_ubicacion; verificar_env; verificar_referencia
  local nombre="${2}_rep${3}"
  local corrida="$CORRIDAS/$cond/$nombre" registro="$CORRIDAS/_registros/$cond/$nombre"
  if [[ -e "$corrida" ]]; then
    echo "==> [$cond / $nombre] retomo la corrida existente"
  else
    echo "==> [$cond / $nombre] preparando la carpeta"
    en_proyecto bash scripts/nueva_corrida.sh "$1" "$2" "$3"
  fi
  mkdir -p "$registro"
  echo
  echo "==> Se abre el agente. Escribile la tarea (la consigna está en TAREA.md)."
  echo "    Cuando termine, salí (/exit en Claude, /quit en Gemini) y la corrida se evalúa sola."
  echo
  local inicio; inicio=$(date +%s)
  en_agente "$corrida" "$registro" interactivo || true
  echo $(( $(date +%s) - inicio )) > "$registro/duracion_segundos.txt"
  ( set -a; source "$RAIZ/.env"; echo "${AGENTE:-claude} $MODELO" ) > "$registro/modelo.txt"
  local ultima; ultima="$(ls -t "$registro"/sesion/projects/*/*.jsonl 2>/dev/null | head -1 || true)"
  [[ -n "$ultima" ]] && cp "$ultima" "$registro/transcript.jsonl"
  # Gemini guarda la conversación en su propia carpeta; se deja una copia a mano.
  ultima="$(ls -t "$registro"/sesion_gemini/tmp/*/chats/*.json 2>/dev/null | head -1 || true)"
  [[ -n "$ultima" ]] && cp "$ultima" "$registro/conversacion_gemini.json"
  echo "==> [$cond / $nombre] evaluando"
  en_proyecto python scripts/evaluar.py "corridas/$cond/$nombre"
}

cmd_todas() {
  local reps=("$@"); [[ ${#reps[@]} -eq 0 ]] && reps=(1 2)
  verificar_imagen; verificar_ubicacion; verificar_env; verificar_referencia
  for rep in "${reps[@]}"; do
    validar_rep "$rep"
    for t in "${ORDEN[@]}"; do
      for c in sin con; do
        local cond; cond="$(condicion "$c")"
        local corrida="$CORRIDAS/$cond/${t}_rep${rep}"
        if [[ -f "$corrida/metricas.json" ]]; then
          echo "--- $cond/${t}_rep${rep}: ya hecha"
        elif [[ -e "$corrida" ]]; then
          echo "--- $cond/${t}_rep${rep}: INCOMPLETA, se saltea (revisarla; repetir con otro número)"
        else
          cmd_correr "$c" "$t" "$rep"
        fi
      done
    done
  done
  cmd_estado
}

cmd_estado() {
  printf "%-6s %-14s %-14s\n" "" "sin_metadatos" "con_metadatos"
  local reps; reps="$(ls -d "$CORRIDAS"/*_metadatos/T*_rep* 2>/dev/null | sed 's/.*_rep//' | sort -un | tr '\n' ' ')"
  [[ -z "$reps" ]] && reps="1 2"
  for rep in $reps; do
    for t in T1 T2 T3; do
      local linea; linea="$(printf "%-6s" "${t}_r$rep")"
      for cond in sin_metadatos con_metadatos; do
        local c="$CORRIDAS/$cond/${t}_rep${rep}" e="pendiente"
        if [[ -f "$c/metricas.json" ]]; then
          e="$(python3 -c "import json,sys; m=json.load(open(sys.argv[1])); print(f\"hecha {m.get('reglas_ok')}/{m.get('reglas_total')}\" if m.get('reglas_total') else 'hecha')" "$c/metricas.json" 2>/dev/null || echo hecha)"
        elif [[ -e "$c" ]]; then e="INCOMPLETA"; fi
        linea+="$(printf " %-14s" "$e")"
      done
      echo "$linea"
    done
  done
}

cmd_revision() {
  verificar_imagen
  en_proyecto python scripts/preparar_revision.py
}

cmd_consolidar() {
  verificar_imagen
  en_proyecto python scripts/consolidar.py
  echo
  echo "Para verlo:  open \"$RAIZ/resultados/reporte.html\""
}

cmd_demo() {
  local cond; cond="$(condicion "${1:-}")"
  verificar_imagen; verificar_ubicacion; verificar_env
  local corrida="$DEMO/$cond/T1_rep1"
  if [[ -e "$corrida" ]]; then
    read -r -p "Ya hay una demo '$1'. ¿Empezar de cero? [s/N] " r
    if [[ "$r" == "s" || "$r" == "S" ]]; then rm -rf "$corrida"; fi
  fi
  if [[ ! -e "$corrida" ]]; then
    CORRIDAS_DIR_CONT=/proyecto/demo en_proyecto bash scripts/nueva_corrida.sh "$1" T1 1
  fi
  clear || true
  echo "DEMO — T1 (modelo dimensional de la capa gold) — escenario: ${cond/_/ }"
  en_agente "$corrida" "" interactivo
}

cmd_demo_comparar() {
  verificar_imagen; verificar_referencia
  for cond in sin_metadatos con_metadatos; do
    [[ -d "$DEMO/$cond/T1_rep1" ]] || error "falta la demo '${cond%%_*}' (./tasd.sh demo ${cond%%_*})"
    CORRIDAS_DIR_CONT=/proyecto/demo en_proyecto python scripts/evaluar.py "demo/$cond/T1_rep1" >/dev/null
  done
  en_proyecto python scripts/comparar.py demo/sin_metadatos/T1_rep1 demo/con_metadatos/T1_rep1
}

cmd_shell() {
  verificar_imagen
  en_proyecto bash
}

# ---------------------------------------------------------------- despacho
comando="${1:-ayuda}"; shift || true
case "$comando" in
  construir) cmd_construir ;;
  datos) cmd_datos ;;
  referencia) cmd_referencia ;;
  autotest) cmd_autotest ;;
  humo) cmd_humo ;;
  preparar) cmd_preparar "$@" ;;
  correr) cmd_correr "$@" ;;
  abrir) cmd_abrir "$@" ;;
  todas) cmd_todas "$@" ;;
  estado) cmd_estado ;;
  evaluar) cmd_evaluar "$@" ;;
  revision) cmd_revision ;;
  consolidar) cmd_consolidar ;;
  demo) cmd_demo "$@" ;;
  demo-comparar) cmd_demo_comparar ;;
  shell) cmd_shell ;;
  ayuda|-h|--help|help) ayuda ;;
  *) echo "Comando desconocido: $comando"; echo; ayuda; exit 1 ;;
esac
