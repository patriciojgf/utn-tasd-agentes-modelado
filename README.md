# Agentes de IA en el ciclo de construcción de un modelo de datos

Tecnologías Aplicadas a Soluciones de Datos (TASD), UTN FRBA, curso K4053, 2.º cuatrimestre de 2026. Grupo 1.

## Qué es esto

Este repositorio tiene todo lo necesario para repetir el experimento de nuestro trabajo práctico cuatrimestral. La pregunta es: ¿hasta dónde pueden los agentes de programación basados en IA hacerse cargo del ciclo de construcción de un modelo de datos (diseño, SQL, tests y documentación)?

El caso de prueba es un banco ficticio con arquitectura medallion (bronze, silver, gold) en dbt Core sobre DuckDB. Un agente de programación (en nuestro caso Claude Code, corriendo en Docker; también se puede usar Gemini CLI) resuelve tres tareas: T1 construir el modelo gold, T2 escribir los tests y T3 documentar. Cada tarea se corre en dos condiciones, sin y con la documentación del negocio, y se mide si el agente aplica bien seis reglas de negocio que no se deducen de los datos.

## Qué hay en el repositorio

| Carpeta | Qué es |
|---|---|
| `base/` | Proyecto dbt con las capas bronze (seeds) y silver ya definidas. Es lo que recibe el agente |
| `metadatos/` | La documentación del negocio que recibe el agente solo en la condición "con metadatos" |
| `tareas/` | La consigna de cada tarea y las instrucciones de cada agente (modelador, tester, documentador) |
| `tareas/pedidos/` | El pedido exacto que se le escribe al agente por consola en cada tarea, con las pistas y las reglas dictadas que se usan si falla una regla |
| `referencia/` | El modelo gold correcto y seis copias con una regla rota cada una (mutantes), para evaluar los tests |
| `scripts/`, `tasd.sh`, `Dockerfile` | Lo necesario para preparar y lanzar una corrida en Docker |
| `docker/`, `requirements.txt`, `.env.example` | Configuración del contenedor del agente, dependencias de Python y plantilla de variables de entorno |
| `docs/` | La guía de evaluación (`EVALUACION.md`), la guía operativa de `tasd.sh` (`GUIA_OPERATIVA.md`) y el pedido de los datos sintéticos |

## Cómo replicarlo

Requisitos: Docker, y una cuenta de Claude (Pro o Max) o una clave de API de Anthropic. Si no tenés Claude, ver más abajo «Usar Gemini en lugar de Claude». Nosotros usamos Claude Code 2.1.274 con el modelo `claude-sonnet-5-5`.

1. Clonar el repositorio fuera de una carpeta sincronizada (Drive, iCloud), por ejemplo en `~/tasd-docker`.
2. Copiar `.env.example` como `.env` y completar `MODELO` y el token. El `.env` nunca se sube.
3. Construir la imagen y la referencia:
   ```bash
   ./tasd.sh construir
   ./tasd.sh referencia
   ```
4. Abrir una corrida y escribirle al agente el pedido de la tarea, que está en `tareas/pedidos/pedido_T1.md`, `pedido_T2.md` y `pedido_T3.md`:
   ```bash
   ./tasd.sh abrir sin T1 1     # sin metadatos, repetición 1
   ./tasd.sh abrir con T1 1     # con metadatos, repetición 1
   ```
   No se interviene hasta que el agente termina. Si falla una regla, se le da la pista de esa regla y, si no alcanza, se le dicta la regla.
5. Evaluar la corrida regla por regla siguiendo [docs/EVALUACION.md](docs/EVALUACION.md), que tiene lo que hay que verificar en cada regla y los valores esperados.

## Usar Gemini en lugar de Claude

El experimento se hizo con Claude Code, pero se puede repetir con Gemini CLI usando una clave de API de Google AI Studio. La imagen de Docker trae las dos herramientas, así que no hay que instalar nada aparte.

### Configuración

1. Sacar una clave en [Google AI Studio](https://aistudio.google.com/apikey) con una cuenta de Google. Alcanza con el nivel gratuito para probar.
2. En `.env`, dejar estas tres variables (y borrar o comentar las de Claude):
   ```
   AGENTE=gemini
   MODELO=gemini-3-flash-preview
   GEMINI_API_KEY=tu_clave
   ```
3. Construir la imagen y la referencia, si no se hizo antes: `./tasd.sh construir` y `./tasd.sh referencia`.
4. Abrir una corrida como siempre, por ejemplo `./tasd.sh abrir sin T1 1`, y pegarle el pedido de `tareas/pedidos/`.
5. Al terminar, salir con `/quit` (en Claude es `/exit`). La corrida se evalúa sola.

### Qué modelo usar

El nombre tiene que ser uno que acepte Gemini CLI. Dentro de una sesión, `/model` muestra la lista. Probados en noviembre de 2026:

| Modelo | Para qué |
|---|---|
| `gemini-3-flash-preview` | Probar que todo el circuito anda; entra cómodo en el nivel gratuito |
| `gemini-3.1-pro-preview` | Repetir la comparación: es el más parecido a Claude Sonnet, pero tiene menos cuota gratuita |

Modelos más viejos como `gemini-2.5-flash` pueden figurar en la API pero la CLI los rechaza con «Model ... was not found or is invalid».

### Cómo saber que quedó bien configurado

Al abrir la corrida, Gemini tiene que mostrar:

- `Authenticated with gemini-api-key`: está usando la clave del `.env`.
- `1 CLAUDE.md file`, abajo a la derecha: cargó las instrucciones del agente.
- `workspace /trabajo`: solo ve la carpeta de la corrida.
- `auto-accept edits`: aprueba solas las ediciones de archivos y pide permiso para los comandos, igual que Claude en el experimento.

### Qué recibe y qué puede hacer

Gemini recibe lo mismo que Claude: lee `CLAUDE.md` y `TAREA.md`, y solo puede leer y escribir archivos de la carpeta de la corrida, correr `dbt`, consultar la base con `python -c` y listar archivos, sin acceso a internet. Esa configuración está en `docker/gemini-settings.json` y se instala como configuración de sistema, así que el agente no la puede cambiar. Cada corrida usa su propia carpeta de sesión, para que una corrida no vea el historial de otra.

El login con cuenta de Google («Sign in with Google») no sirve: Google lo dio de baja en Gemini CLI para cuentas personales, incluidas las de Google AI Pro, en junio de 2026. Por eso se usa la clave de API.

Los resultados no son comparables uno a uno con los del informe, porque cambia el modelo. Sí se puede repetir la comparación sin y con metadatos con Gemini.

## Documentación completa

La guía detallada de `tasd.sh`, con todos los comandos y los problemas frecuentes, está en [docs/GUIA_OPERATIVA.md](docs/GUIA_OPERATIVA.md). El informe y la presentación del trabajo no están en este repositorio.

## Integrantes

- Aldo Callisaya
- Patricio García Farrell
- Santiago Chejolan
- Fausto Rodríguez
