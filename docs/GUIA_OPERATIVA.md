# Guía operativa

Esta es la guía detallada de uso de `tasd.sh`. Para una introducción al experimento, ver el [README](../README.md).

Este proyecto tiene todo lo necesario para correr la parte práctica del TP, obtener los resultados
y hacer la demo en clase. Todo corre dentro de Docker, con versiones fijas: en la Mac solo hace
falta **Docker Desktop**. No hay que instalar Python, dbt ni Claude Code.

Todo se maneja con un solo script: `./tasd.sh`. Si se corre sin argumentos, muestra la ayuda.

## Cómo está armado

```
            ┌──────────────────── contenedor "proyecto" ─────────────────────┐
            │  ve todo el proyecto: base, metadatos, referencia, scripts     │
            │  arma corridas · construye la referencia · evalúa · consolida  │
            └────────────────────────────────────────────────────────────────┘
                     │ crea corridas/<escenario>/<tarea>_rep<n>/
                     ▼
            ┌──────────────────── contenedor "agente" ───────────────────────┐
            │  Claude Code. SOLO ve la carpeta de su corrida (/trabajo):     │
            │  datos, consigna, instrucciones y, en "con", la metadata       │
            │  sin internet, sin la referencia, sin la configuración local   │
            └────────────────────────────────────────────────────────────────┘
```

Que el agente no pueda ver la solución no depende de que "no la busque": la carpeta no existe
dentro de su contenedor. Además corre con un Claude Code limpio, sin la configuración ni la
memoria de quien lo ejecuta, así que las corridas no dependen de la computadora.

| Componente | Versión |
|---|---|
| Python | 3.13.15 |
| dbt-core / dbt-duckdb | 1.12.5 / 1.11.0 |
| DuckDB | 1.5.5 |
| Claude Code | 2.1.274, sin actualizaciones automáticas |
| Modelo | el que fije el grupo en `.env` |

## 1. Preparación (una sola vez)

**1.1. Copiar el proyecto fuera de Google Drive.** DuckDB escribe todo el tiempo en su archivo y la
sincronización de Drive puede trabarlo. El script avisa si se lo corre desde Drive.

```bash
git clone https://github.com/<usuario>/tasd-tpc-agentes.git ~/tasd-docker
```

```bash
cd ~/tasd-docker
```

**1.2. Abrir Docker Desktop** y esperar a que diga que está corriendo.

**1.3. Configurar el agente.** Copiar `.env.example` como `.env` y completarlo:

```bash
cp .env.example .env
```

- `MODELO`: el nombre completo del modelo, por ejemplo el que muestra `/model` dentro de `claude`.
  No usar un alias como "sonnet", porque puede cambiar de versión con el tiempo.
- `CLAUDE_CODE_OAUTH_TOKEN`: con una cuenta Pro o Max, se genera en la Mac con el comando de abajo
  y se pega el token que devuelve. Como alternativa, se puede usar `ANTHROPIC_API_KEY`.

```bash
claude setup-token
```

El `.env` es personal: no lo suban a Drive ni lo compartan.

**1.4. Construir la imagen, la referencia y verificar:**

```bash
./tasd.sh construir
```

```bash
./tasd.sh referencia
```

```bash
./tasd.sh autotest
```

```bash
./tasd.sh humo
```

- `construir` tarda unos minutos la primera vez y al final muestra las versiones instaladas.
- `referencia` construye la solución correcta y muestra los números de la Tabla 2 del informe
  (400 de 581 clientes, 18.772 de 20.000 movimientos y 6 de 13 productos).
- `autotest` comprueba el evaluador con resultados simulados, sin usar el agente. Tiene que
  terminar con `Autotest OK`.
- `humo` muestra qué ve el agente en cada escenario y confirma que no puede ver la referencia.

**Datos nuevos (opcional).** Si el grupo genera los datos con otra IA (`docs/Pedido_datos_sinteticos.md`),
hay que reemplazar `scripts/generar_datos.py`, correr `./tasd.sh datos` y después
`./tasd.sh referencia` y `./tasd.sh autotest`. Con los números nuevos se actualiza la Tabla 2.

## 2. Piloto

Correr T1 una vez en cada escenario, con un número de repetición que no se use después (por ejemplo, 0):

```bash
./tasd.sh correr sin T1 0
```

```bash
./tasd.sh correr con T1 0
```

Cada comando arma la carpeta, deja trabajar al agente sin intervención y al final muestra la
evaluación. Qué mirar:

- Que el agente haya terminado: `agente_termino_ok` en `True`.
- Cuánto tardó: `duracion_segundos`.
- Cuántas de las 4 reglas resuelve en cada escenario. Si resuelve las 4 sin metadatos, las reglas
  se deducen de los datos y hay que revisar el diseño antes de seguir.

Las corridas del piloto quedan en `corridas/*/T1_rep0` y aparecen en el consolidado. Se pueden
borrar cuando el grupo esté conforme.

**Después del piloto, congelar el diseño.** No se tocan datos, consignas, agentes, metadata, modelo
ni la imagen hasta terminar las 12 corridas. Antes de ver resultados hay que acordar los criterios de
clasificación, que están en `scripts/consolidar.py`, en la función `clasificar()`.

## 3. Las 12 corridas

```bash
./tasd.sh todas
```

Corre las repeticiones 1 y 2 de T1, T2 y T3 en los dos escenarios, alternándolos, y evalúa cada una.
Se puede cortar y volver a lanzar: saltea las que ya están hechas. Si una corrida quedó incompleta
(por ejemplo, por el límite de uso de la cuenta), no la pisa: se repite con otro número y se anota
en el informe.

```bash
./tasd.sh correr sin T1 3
```

**Modo interactivo.** Si preferís escribirle vos la tarea a Claude, en lugar de `correr` usá:

```bash
./tasd.sh abrir sin T1 1
```

Se arma la carpeta, se abre Claude dentro del contenedor (solo ve esa carpeta) y le escribís la tarea. Al salir con `/exit` se guarda la sesión y se evalúa. Para que las corridas sean comparables, conviene escribirle siempre el mismo mensaje.

Para ver cómo va el experimento:

```bash
./tasd.sh estado
```

Cada corrida deja:

| Dónde | Qué |
|---|---|
| `corridas/<escenario>/<tarea>_rep<n>/` | El proyecto dbt tal como lo dejó el agente: SQL, `schema.yml`, `RESUMEN.md`, tests |
| `corridas/<escenario>/<tarea>_rep<n>/metricas.json` | La evaluación automática |
| `corridas/_registros/<escenario>/<tarea>_rep<n>/` | `transcript.jsonl` (todo lo que hizo el agente), duración, modelo, versión y errores |

## 4. Evaluación y resultados

Qué se evalúa solo:

| Tarea | Cómo se evalúa |
|---|---|
| T1 (modelo) | El agente elige los nombres y el diseño, así que cada tabla se identifica por su contenido (hecho, dimensión de clientes, de productos y de cuentas). Se controla que compile y pase sus tests, las 6 reglas contra la referencia (movimiento por movimiento) y la estructura: que existan el hecho y las dimensiones y que las claves del hecho estén en sus dimensiones |
| T2 (tests) | Los tests del agente se corren sobre 6 versiones de la referencia con una regla rota a propósito (`referencia/mutantes/`). Si algún test falla, esa regla queda cubierta |
| T3 (documentación) | Solo la cobertura (cuántas columnas tienen descripción). Si lo que dice es correcto se revisa a mano |
| Todas | Si el agente modificó algo prohibido (seeds, silver, configuración o, en T2 y T3, el SQL gold). También la duración, los turnos, los tokens y el costo |

**Revisión manual a ciegas (diseño de T1 y documentación de T3):**

```bash
./tasd.sh revision
```

Copia en orden aleatorio el modelo de cada corrida de T1 (`revision_ciega/modelo/M01, ...`) y la
documentación de cada corrida de T3 (`revision_ciega/documentacion/D01, ...`). Deja dos planillas:
`planilla_diseno.csv` (si el diseño es aceptable, con observaciones) y `planilla.csv` (cada regla
documentada como correcta, inventada o ausente). Las
instrucciones están en `INSTRUCCIONES.md`. Es mejor que la haga alguien que no corrió el experimento.
La clave queda aparte, en `resultados/revision_ciega_CLAVE.csv`, y no se le pasa a quien revisa.

**Consolidar:**

```bash
./tasd.sh consolidar
```

Genera:
- `resultados/metricas_consolidadas.csv`: una fila por corrida.
- `resultados/reporte.md`: las tablas para el informe.
- `resultados/reporte.html`: lo mismo con gráficos, para mostrar en clase.

Las tablas muestran:
- Quién resuelve cada etapa.
- Qué reglas respeta el modelo.
- Qué reglas detectan los tests y cuáles están bien documentadas, sin y con metadatos.
- La duración y el costo.

Al terminar, copiar `corridas/` y `resultados/` a Drive para que lo vea el grupo.

## 5. Demo en clase

Se muestra T1 en los dos escenarios, lado a lado, con el agente trabajando en vivo.
Hay que abrir dos ventanas de Terminal en `~/tasd-docker`.

Ventana izquierda:

```bash
./tasd.sh demo sin
```

Ventana derecha:

```bash
./tasd.sh demo con
```

En las dos se pega el mismo mensaje (lo muestra la pantalla):
`Leé TAREA.md y resolvé la tarea siguiendo las instrucciones de CLAUDE.md.`

El agente tiene los mismos permisos que en las corridas del experimento. Cuando terminen las dos,
se sale con `/exit` y se comparan:

```bash
./tasd.sh demo-comparar
```

Muestra lado a lado:
- Si cada versión compila y pasa sus propios tests: normalmente sí, en las dos.
- La suma en pesos contra la correcta.
- Qué reglas respetó cada una.

Ese es el punto de la demo: las dos "funcionan", pero solo una tiene los números bien.

**Recomendaciones:**
- Ensayar antes. Si T1 tarda más de lo que da la presentación, conviene arrancar las dos, mostrar
  los primeros pasos y pasar a `reporte.html` con los resultados de las 12 corridas.
- Tener grabada una demo completa por si falla la conexión o se agota el uso de la cuenta.
- `./tasd.sh demo sin` pregunta si se quiere empezar de cero cuando ya hay una demo hecha.

## Estructura

```
tasd-docker/
├── tasd.sh                  punto de entrada (ver ./tasd.sh)
├── Dockerfile               imagen con Python, dbt, DuckDB y Claude Code (versiones fijas)
├── docker/agente.sh         cómo se lanza el agente (prompt, permisos), igual en experimento y demo
├── .env.example             modelo y autenticación del agente
├── base/                    proyecto dbt que recibe el agente: seeds (bronze) y silver sin documentar
├── metadatos/               lo que se agrega en el escenario "con": schema.yml documentado y reglas
├── tareas/                  consignas T1 a T3 e instrucciones de los tres agentes
├── referencia/              solución correcta y mutantes (el agente nunca la ve)
├── scripts/                 generar datos, armar corridas, evaluar, consolidar, revisión, autotest
├── docs/                    pedido de datos sintéticos para otra IA
├── corridas/                se genera: una carpeta por corrida
├── demo/                    se genera: las dos sesiones de la demo
└── resultados/              se genera: CSV, reportes y revisión ciega
```

## Problemas frecuentes

| Síntoma | Qué hacer |
|---|---|
| `Docker no está corriendo` | Abrir Docker Desktop y esperar a que termine de iniciar |
| `Falta la imagen` | `./tasd.sh construir` |
| `Falta la referencia` | `./tasd.sh referencia` |
| `Falta el archivo .env` o falta el token | Paso 1.3 |
| El agente termina enseguida con código 1 | Leer `corridas/_registros/.../errores_agente.txt`: casi siempre es el token vencido o un nombre de modelo mal escrito |
| `ya existe ...` | Esa corrida ya se hizo. Si se cortó, repetirla con otro número y anotarlo |
| `Could not set lock on file` | Hay otro proceso usando la misma base. Cerrar `./tasd.sh shell` u otras terminales |
| `Permission denied` al correr `./tasd.sh` | `chmod +x tasd.sh` |
