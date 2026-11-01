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

El experimento se hizo con Claude Code, pero se puede repetir con Gemini CLI, por ejemplo con una cuenta de Google (gratuita o Google AI Pro) o con una clave de API de Google AI Studio. La imagen de Docker trae las dos herramientas.

1. En `.env`, poner `AGENTE=gemini` y el modelo en `MODELO` (por ejemplo `gemini-2.5-pro`).
2. Autenticarse de una de estas formas:
   - Con cuenta de Google, una sola vez: `./tasd.sh gemini-login`. Se abre Gemini dentro del contenedor, se elige «Login with Google», se abre el link en el navegador y se pega el código. Las credenciales quedan en `.gemini-auth/`, que no se sube al repositorio.
   - Con clave de API: completar `GEMINI_API_KEY` en `.env`.
3. Seguir los mismos pasos de arriba (`./tasd.sh abrir ...`).

Gemini recibe lo mismo que Claude: lee `CLAUDE.md` y `TAREA.md`, y solo puede leer y escribir archivos de la carpeta de la corrida, correr `dbt`, consultar la base con `python -c` y listar archivos, sin acceso a internet. Esa configuración está en `docker/gemini-settings.json` y se instala como configuración de sistema, así que el agente no la puede cambiar. Cada corrida usa su propia carpeta de sesión, para que una corrida no vea el historial de otra.

Tené en cuenta que los resultados no son comparables uno a uno con los del informe, porque cambia el modelo. Sí se puede repetir la comparación sin y con metadatos con Gemini.

## Documentación completa

La guía detallada de `tasd.sh`, con todos los comandos y los problemas frecuentes, está en [docs/GUIA_OPERATIVA.md](docs/GUIA_OPERATIVA.md). El informe y la presentación del trabajo no están en este repositorio.

## Integrantes

- Aldo Callisaya
- Patricio García Farrell
- Santiago Chejolan
- Fausto Rodríguez
