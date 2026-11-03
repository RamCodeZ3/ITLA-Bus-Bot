# ITLA Tickets API

API REST sin persistencia para validar credenciales del Campus Virtual del ITLA,
reservar y comprar boletos de transporte y recuperar sus imágenes. Python 3.12,
FastAPI, uv, Playwright y Lightpanda. El README está en español; el código, los
mensajes de error y los logs están en inglés.

## Responsabilidades

La aplicación cliente almacena usuarios, credenciales y horarios en el dispositivo,
programa recordatorios y obtiene la confirmación del usuario. Envía las credenciales
y los viajes concretos en cada petición. Esta API no registra usuarios, conserva
sesiones entre peticiones ni utiliza una base de datos.

La API conserva el catálogo estático de rutas y paradas, valida las selecciones,
ejecuta la automatización y devuelve imágenes PNG codificadas en base64.

## Ejecutar con Docker

```bash
cp .env.example .env
# Cambia API_KEY por un valor aleatorio de al menos 16 caracteres.
docker compose up --build
```

La API escucha en `http://localhost:10000`; OpenAPI está en `/docs`. El contenedor
usa un usuario sin privilegios e incluye Lightpanda **1.0.2** y Chromium. Solo
publica el puerto HTTP: CDP escucha en `127.0.0.1:9222` dentro del contenedor.
En una prueba local, Lightpanda 1.0.2 convirtió un canvas de 120×120 en un PNG
de 1×1. Por eso el motor predeterminado usa Lightpanda para navegar y Chromium
para generar imágenes.

El Dockerfile admite `TARGETARCH=amd64` y `TARGETARCH=arm64`; en Compose configura
`TARGETARCH=arm64` si corresponde a tu máquina.

## Desarrollo con uv

```bash
uv sync --frozen
uv run playwright install --with-deps chromium
cp .env.example .env
```

Instala el binario de Lightpanda 1.0.2 para tu arquitectura desde sus
[publicaciones oficiales](https://github.com/lightpanda-io/browser/releases/tag/1.0.2)
y configura `LIGHTPANDA_PATH`. La aplicación lo inicia y detiene automáticamente.
Como alternativa aprobada, `BROWSER_ENGINE=chromium` ejecuta todo con Chromium.

```bash
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 10000 --workers 1 --no-access-log
```

El archivo `.env` antiguo puede contener variables obsoletas: sustituye su contenido
por la configuración actual. Nunca agregues ese archivo al repositorio.

## Render

Se incluye `render.yaml` para crear un Web Service mediante Blueprint, usando el
Dockerfile y una API key generada por Render. También puedes crear el servicio
Docker manualmente y definir las variables de `.env.example`. Configura `/health`
como health check. Uvicorn respeta el `PORT` proporcionado por Render y escucha
en `0.0.0.0`.

Render documenta un límite de hasta **100 minutos por respuesta HTTP** en sus
[comparaciones oficiales](https://render.com/docs/render-vs-heroku-comparison).
La API establece su propio límite conservador de **180 segundos**, configurable
con `REQUEST_TIMEOUT`; el cliente debe permitir un margen adicional y el arranque
en frío. No se implementa un modo de trabajos asíncronos.

En el plan gratuito, el servicio puede suspenderse tras 15 minutos sin tráfico;
el sistema de archivos es efímero. Consulta la
[documentación de servicios gratuitos](https://render.com/docs/free).
Un reinicio o suspensión pierde el trabajo en curso. **Un timeout no demuestra
que la compra haya fallado:** consulta `/get-tickets` y verifica el Campus antes
de volver a comprar. No configures reintentos automáticos para `/buy-tickets`.

Usa un único proceso Uvicorn y una instancia. El límite de concurrencia y la
protección de compras simultáneas son locales al proceso. El consumo de memoria
de Chromium y Lightpanda debe medirse en tu instancia de Render; todavía no hay
una validación de carga en ese hosting.

## Variables de entorno

| Variable | Valor predeterminado | Uso |
|---|---|---|
| `API_KEY` | Obligatoria, mínimo 16 caracteres | Cabecera `X-API-Key` |
| `BROWSER_ENGINE` | `lightpanda` | `lightpanda` o `chromium` |
| `LIGHTPANDA_PATH` | `/usr/local/bin/lightpanda` | Binario de versión fija |
| `LIGHTPANDA_HOST` | `127.0.0.1` | Solo loopback, no configurable a una IP pública |
| `LIGHTPANDA_PORT` | `9222` | Puerto CDP interno |
| `BROWSER_START_TIMEOUT` | `30` | Segundos para iniciar el navegador |
| `PAGE_TIMEOUT_MS` | `30000` | Timeout de acciones y esperas del portal |
| `REQUEST_TIMEOUT` | `180` | Segundos de toda la operación, incluida la espera de capacidad |
| `MAX_CONCURRENT_SESSIONS` | `1` | Flujos concurrentes; incluye la fase de imágenes |
| `ALLOWED_ORIGINS` | `[]` | Lista JSON de orígenes CORS autorizados |
| `LOG_LEVEL` | `INFO` | Nivel de logs JSON por consola |
| `PORT` | `10000` | Puerto HTTP del comando del contenedor |

Las contraseñas viajan en el cuerpo de peticiones HTTPS. No se usa Fernet adicional.
Nunca incluyas credenciales en URLs, parámetros de consulta o logs.

## Contrato HTTP

Base: `/api/v1/itla-tickets`. Todos los endpoints de esta base requieren
`X-API-Key`. `/health` es público y no expone configuración. Las respuestas
incluyen `X-Correlation-ID` generado por el servidor y `Cache-Control: no-store`.

### Validar credenciales

`POST /login`

```json
{"username":"student@itla.edu.do","password":"your-password"}
```

Devuelve `200 {"valid":true}` o `401` con `INVALID_CREDENTIALS`. Conserva la
verificación actual: espera un control visible de sesión iniciada o de rechazo;
un cambio de URL por sí solo no demuestra que el login funcionó. Un login
que no puede confirmarse por disponibilidad o timeout devuelve `503`.

### Consultar rutas

`GET /routes`

Devuelve `weekday` y `saturday`, cada uno con rutas de `arrival` y `departure`;
`arrival.stops_by_route` relaciona rutas y paradas. Usa los valores completos
exactos del catálogo, incluidas las horas y los acentos, sin truncarlos.

### Comprar boletos

`POST /buy-tickets`

```json
{
  "username": "student@itla.edu.do",
  "password": "your-password",
  "trips": [
    {
      "date": "2026-11-04",
      "arrival_route": "27 de Febrero 8:00AM",
      "pickup_stop": "PINTURA AVE. ISABEL AGUIAR (Después de cruzar) PARADA OMSA",
      "departure_route": "27 de Febrero 6:00PM"
    }
  ]
}
```

Consulta `/routes` para seleccionar los valores válidos del catálogo.
Cada viaje es de **entrada y salida juntas**, conservando el flujo existente.
No se admiten viajes de un solo sentido en esta versión. Las rutas incluyen
sus horas; no hay campos `arrival_time` o `departure_time` independientes.

Se admiten entre uno y siete viajes, uno por fecha, de lunes a sábado. La parada
debe pertenecer a la ruta de llegada. Si el catálogo no tiene paradas para una
ruta, el valor heredado es `Única parada`. Las selecciones incorrectas devuelven
`422`. El catálogo es una validación estática; la disponibilidad real se verifica
en el portal y puede cambiar.

Antes de reservar se verifica el saldo usando el precio heredado de RD$30 por
sentido y se rechazan fechas con reservas existentes. No se reintenta un pago.
El portal debe mostrar el control de boletos comprados para confirmar el pago.
La protección es preventiva, no una garantía de exactamente una compra ante
reinicios o acciones concurrentes desde otras aplicaciones.

Una petición con varios viajes no es una transacción: si falla uno después de
comprar otro, los anteriores pueden estar pagados. Verifica todos en el Campus
antes de reintentar. Se recomienda enviar un viaje por petición.

Respuesta:

```json
{
  "tickets": [
    {
      "id": "2026-11-04-entry",
      "filename": "2026-11-04-entry.png",
      "content_type": "image/png",
      "data_base64": "..."
    }
  ]
}
```

Los identificadores describen fecha y sentido; no son identificadores oficiales
del portal. Si todos los pagos se confirman pero falla la generación de imágenes,
se devuelve `200 {"tickets":[]}`. Recupera las imágenes con `/get-tickets`; esa
respuesta no debe provocar otra compra.

### Recuperar boletos existentes

`POST /get-tickets`, con el mismo cuerpo de credenciales que `/login`.

Devuelve la misma estructura de imágenes. No reserva ni paga. Selecciona la
primera fila comprada con
`usage_date >= today`, en el orden visible del portal, usando la zona horaria
`America/Santo_Domingo`. Si existen entrada y salida, devuelve ambos boletos;
si solo existe uno de los dos, devuelve únicamente ese boleto. Los sentidos
ausentes, ocultos o deshabilitados se omiten. Si no encuentra
una fila, devuelve `200 {"tickets":[]}`. No busca automáticamente en otras páginas
de la tabla. Una fila ambigua para una fecha produce `409`.

### Salud y errores

`GET /health` devuelve `200` cuando la conexión real al navegador y el motor de
imágenes están listos, o `503` cuando no lo están. La disponibilidad del Campus
se evalúa al ejecutar los flujos, no en cada health check.

Todos los errores usan:

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid credentials.",
    "correlation_id": "generated-uuid"
  }
}
```

| Estado | Situación |
|---|---|
| `401` | API key o credenciales incorrectas |
| `422` | Cuerpo, fecha, ruta o parada inválidos |
| `409` | Saldo insuficiente, reserva existente, selección ambigua o compra simultánea |
| `502` | Fallo del portal, imágenes inválidas o resultado de pago desconocido |
| `503` | Navegador o login del Campus no disponible |
| `504` | Timeout del flujo; el resultado del pago puede ser desconocido |
| `500` | Fallo interno inesperado, sin detalles sensibles |

## Arquitectura

```text
app/
  main.py                    FastAPI factory y lifespan
  config.py                  Configuración validada
  presentation/              Rutas HTTP, esquemas, autenticación y errores
  application/               Bus, registro de respuestas, handlers y puertos
  domain/                    Modelos, eventos inmutables y excepciones
  infrastructure/
    browser/                 Proceso Lightpanda, CDP y contextos aislados
    scraper/
      pages/                 Login, inicio Campus, Transporte y Reservas
      flows/                 Login, compra y recuperación
      gateway.py             Implementación del puerto de tickets
  routes_data.py             Catálogo estático heredado
tests/                       Pruebas sin cuenta real y pruebas de navegador opt-in
```

Cada endpoint publica un evento con `correlation_id` y fecha UTC; un handler
asíncrono ejecuta el flujo y publica éxito o fallo; el listener resuelve su
`asyncio.Future`. No hay broker, cola durable ni historial de eventos.

**Los eventos no contienen contraseñas ni imágenes.** Los datos privados viven en
un registro en memoria durante la petición y se eliminan al responder, cancelar
o agotar el timeout. Los handlers convierten errores en eventos de fallo.
Cada petición crea contextos nuevos, cerrados en `finally`. La fase de imágenes
usa un contexto nuevo de Chromium y vuelve a autenticarse.

Lightpanda mantiene un proceso y una conexión CDP, con reconexión antes de flujos
posteriores. El arranque espera readiness antes de servir tráfico. Las imágenes
se interceptan en el navegador como URLs `data:` o `blob:` y se leen a memoria;
no se usa `Download.save_as`, screenshots a disco ni directorios temporales para
boletos. La captura valida la cabecera PNG y rechaza imágenes de un píxel.

## Pruebas y límites de validación

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Las pruebas normales cubren contratos HTTP, errores sin credenciales, validación
del catálogo, handlers, correlación, limpieza tras cancelación, timeouts,
confirmación del login y protección de compras.

Las pruebas reales de navegador son opt-in y no compran boletos:

```bash
TEST_LIGHTPANDA_PATH=/path/to/lightpanda uv run pytest -m live -v
```

Comprueban aislamiento de cookies, interacción DOM, salud, recuperación tras
terminar Lightpanda y captura de canvas PNG con URLs `data:` y `blob:` sin eventos
de descarga. No sustituyen una prueba autenticada del Campus: hacen falta una
cuenta de prueba y una validación controlada del pago real antes de afirmar que
el flujo completo funciona con la versión actual del portal. No se han incluido
credenciales de estudiantes ni pruebas de pago automáticas en CI.

Para probar contra una cuenta real, configura `CAMPUS_TEST_USERNAME` y
`CAMPUS_TEST_PASSWORD` únicamente en tu entorno local y ejecuta
`uv run pytest -m live tests/test_campus_live.py -k "not purchase"`.
No compartas esos valores en commits, capturas ni registros. La prueba de compra
requiere además `CAMPUS_ALLOW_PURCHASE=1` y `CAMPUS_TEST_TRIP_JSON` con un viaje
válido; produce un cargo real y debe ejecutarse de forma controlada.
