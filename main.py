import asyncio
import json
import unicodedata
from playwright.async_api import async_playwright

URL_CAMPUS = "https://campusvirtual.itla.edu.do"
SESSION_FILE = "session.json"

CREDENCIALES = {
    "usuario": "usuario",
    "password": "password"
}

BOLETO = {
    "tipo": "EntradaySalida",  # "EntradaySalida" | "entrada" | "salida"
    "fecha": "2026-03-10",
    "hora_entrada": "John F. Kennedy / San Vicente de Paul 8:00AM",
    "parada_subida": "Plaza Galerías del Este",
    "hora_salida": "John F. Kennedy / San Vicente de Paul 6:00PM",
    "parada_llegada": "Metro María Montes"
}


async def guardar_sesion(context):
    cookies = await context.cookies()
    with open(SESSION_FILE, "w") as f:
        json.dump(cookies, f)
    print("💾 Sesión guardada")


async def cargar_sesion(context):
    try:
        with open(SESSION_FILE) as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("📂 Sesión cargada")
        return True
    except FileNotFoundError:
        return False


async def hacer_login(page):
    print("🔐 Haciendo login...")
    await page.goto(URL_CAMPUS)
    await page.wait_for_load_state("networkidle")

    email_input = page.locator("#email")
    await email_input.click()
    await email_input.press_sequentially(CREDENCIALES["usuario"], delay=50)

    password_input = page.locator("#password")
    await password_input.click()
    await password_input.press_sequentially(CREDENCIALES["password"], delay=50)

    await page.get_by_role("button", name="Iniciar Sesión").click()
    await page.wait_for_timeout(3000)
    await page.wait_for_load_state("networkidle")

    try:
        await page.wait_for_selector(".btn-logout, button:has-text('Salir')", timeout=5000)
        print("✅ Login exitoso")
        return True
    except:
        pass

    if await page.locator("#email").count() > 0:
        await page.screenshot(path="debug_login.png")
        error = page.locator(".alert-danger, .error-msg, .invalid-feedback, .text-danger")
        if await error.count() > 0:
            print(f"  ❌ Error: {await error.first.inner_text()}")
        print("❌ Login fallido — revisa debug_login.png")
        return False

    print("✅ Login exitoso")
    return True


async def ir_a_transporte(page):
    print("🚌 Navegando a Transporte...")

    servicios_header = page.locator(".botton_line2")
    if await servicios_header.count() > 0:
        await servicios_header.click()
        await page.wait_for_timeout(800)

    await page.locator("li.pointer a", has_text="Transporte").click()
    await page.wait_for_url("**/customers/home**", timeout=15000)
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(2000)
    print(f"✅ En transporte → {page.url}")


def normalizar(s):
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


async def ngx_select(page, field_id, texto_parcial, nombre):
    await page.locator(f"ngx-select-dropdown#{field_id} .ngx-dropdown-button").click()
    await page.wait_for_timeout(1000)

    opciones = page.locator(f"ngx-select-dropdown#{field_id} .available-item")
    count = await opciones.count()

    if count == 0:
        print(f"  ⚠️  No se abrió el dropdown de {nombre}")
        await page.keyboard.press("Escape")
        return

    busqueda = normalizar(texto_parcial)
    for i in range(count):
        texto = await opciones.nth(i).inner_text()
        if busqueda in normalizar(texto):
            await opciones.nth(i).click()
            print(f"  ✓ {nombre}: {texto.strip()}")
            return

    print(f"  ⚠️  '{texto_parcial}' no encontrado en {nombre}. Opciones disponibles:")
    for i in range(min(count, 15)):
        print(f"      [{i}] {(await opciones.nth(i).inner_text()).strip()}")
    await page.keyboard.press("Escape")


async def reservar_boleto(page):
    print("📝 Llenando formulario...")

    await page.wait_for_selector("client-ticket-reserve", timeout=10000)
    await page.wait_for_selector("#reserve_date", timeout=10000)

    await page.locator(f"#{BOLETO['tipo']}").check()
    print(f"  ✓ Tipo: {BOLETO['tipo']}")

    await page.locator("#reserve_date").fill(BOLETO["fecha"])
    print(f"  ✓ Fecha: {BOLETO['fecha']}")

    await ngx_select(page, "time_in", BOLETO["hora_entrada"], "Hora entrada")
    await ngx_select(page, "stop_in", BOLETO["parada_subida"], "Parada subida")
    await ngx_select(page, "time_out", BOLETO["hora_salida"], "Hora salida")
    await ngx_select(page, "stop_out", BOLETO["parada_llegada"], "Parada llegada")

    print("✅ Formulario completado")


async def confirmar_reserva(page):
    print("🚀 Enviando reserva...")
    await page.get_by_role("button", name="Reservar").click()
    await page.wait_for_load_state("networkidle")
    await page.screenshot(path="confirmacion.png")
    print("✅ Listo — screenshot en confirmacion.png")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page    = await context.new_page()

        sesion_ok = await cargar_sesion(context)

        if sesion_ok:
            await page.goto(URL_CAMPUS)
            await page.wait_for_load_state("networkidle")
            if "login" in page.url.lower():
                print("⚠️  Sesión expirada, relogueando...")
                sesion_ok = False

        if not sesion_ok:
            ok = await hacer_login(page)
            if not ok:
                await browser.close()
                return
            await guardar_sesion(context)

        await ir_a_transporte(page)
        await reservar_boleto(page)

        print("\n⏸️  Revisa el navegador. ENTER para confirmar...")
        input()

        await confirmar_reserva(page)
        await browser.close()
        print("\n🎉 Listo.")


if __name__ == "__main__":
    asyncio.run(main())