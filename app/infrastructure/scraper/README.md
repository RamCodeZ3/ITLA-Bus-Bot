# Scraper con Lightpanda

El scraper de reservas se conecta a un servidor Lightpanda mediante CDP.
Playwright sigue siendo el cliente; `chromium.connect_over_cdp` es el nombre
de su API de conexión y no inicia Chrome.

## Ejecución

Instala Lightpanda siguiendo su [documentación oficial](https://lightpanda.io/docs/).
Inicia el servidor antes de ejecutar el bot:

```sh
lightpanda serve --host 127.0.0.1 --port 9222
```

Por defecto se utiliza `ws://127.0.0.1:9222`. Para otro servidor, configura
`LIGHTPANDA_CDP_URL` en el entorno del bot. Cada ejecución crea y cierra su
propio contexto para aislar las cuentas. El servidor se administra por separado
y debe permanecer disponible mientras se ejecuta el bot. No hay retorno
automático a Chrome si la conexión falla.

Referencia: [Playwright con Lightpanda](https://lightpanda.io/docs/usage/cdp/playwright).

## Verificación

Desde la raíz del repositorio:

```sh
PYTHONPATH=app .venv/bin/python -m unittest discover \
  -s app/infrastructure/scraper -p 'test_*.py' -v
```

Para incluir la prueba de integración con el servidor real:

```sh
PYTHONPATH=app LIGHTPANDA_INTEGRATION=1 \
  .venv/bin/python -m unittest discover \
  -s app/infrastructure/scraper -p 'test_*.py' -v
```

La integración utiliza un formulario ficticio; no accede al portal ITLA.
Las pruebas verifican interacción con formularios, interrupción ante errores
y cierre de sesiones. No validan la compra ni la generación de boletos.

Para comprobar una reserva real sin pagar, ejecuta únicamente `login`,
`go_to_transport`, `balance_verification`, `fill_form`, `confirm_reserve`
y `go_to_reserve_page`, verificando la fila de la fecha solicitada.
Comprueba primero si ya existe una reserva para evitar duplicarla.
**No ejecutes `run()` para esta comprobación: incluye `confirm_buy` y descargas.**

## Limitaciones

- `app/services/authentication.py` sigue utilizando Chromium. Su migración
  queda fuera del alcance de esta carpeta.
- Las descargas requieren primero una compra. Su validación real queda pendiente
  cuando la prueba autorizada termina en la reserva.
- Lightpanda no ofrece el mismo renderizado que Chrome. Si el portal genera
  el PNG o QR con canvas, hace falta verificar el contenido del boleto, además
  de que se emita la descarga. Las
  [notas oficiales de versiones](https://github.com/lightpanda-io/browser/releases)
  documentan implementaciones de canvas que devuelven un PNG de 1 × 1 píxel.
  Cambiar el cliente CDP no resuelve esa limitación.
