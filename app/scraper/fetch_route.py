import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


URL_CAMPUS = "https://campusvirtual.itla.edu.do"


async def login(page, credentials):
    print("🔐 Logging in...")
    await page.goto(URL_CAMPUS)
    await page.wait_for_load_state("networkidle")

    await page.locator("#email").click()
    await page.keyboard.type(credentials["email"], delay=50)
    await page.locator("#password").click()
    await page.keyboard.type(credentials["password"], delay=50)

    await page.get_by_role("button", name="Iniciar Sesión").click()
    await page.wait_for_timeout(3000)
    await page.wait_for_load_state("networkidle")

    try:
        await page.wait_for_selector(".btn-logout, button:has-text('Salir')", timeout=5000)
        print("✅ Login exitoso")
        return True
    except Exception:
        print("❌ Login fallido")
        return False


async def go_to_transport(page):
    print("🚌 Navegando a Transporte...")
    await page.locator("li.pointer a", has_text="Transporte").click()
    await page.wait_for_url("**/customers/home**", timeout=15000)
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(2000)
    print(f"✅ En pagina de transporte → {page.url}")


async def close_any_open_dropdown(page):
    """Cierra cualquier dropdown abierto presionando Escape y haciendo click fuera."""
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(300)
    # Click en zona neutra del formulario para asegurarse
    try:
        await page.locator("client-ticket-reserve").click(position={"x": 10, "y": 10}, timeout=1000)
    except Exception:
        pass
    await page.wait_for_timeout(300)


async def is_enabled(page, field_id) -> bool:
    btn = page.locator(f"ngx-select-dropdown#{field_id} .ngx-dropdown-button")
    classes = await btn.get_attribute("class") or ""
    return "ngx-disabled" not in classes


async def wait_enabled(page, field_id, timeout_ms=6000):
    for _ in range(timeout_ms // 300):
        if await is_enabled(page, field_id):
            return True
        await page.wait_for_timeout(300)
    return False


async def get_options(page, field_id) -> list[str]:
    items = page.locator(f"ngx-select-dropdown#{field_id} .available-item")
    count = await items.count()
    return [( await items.nth(i).inner_text()).strip() for i in range(count)]


async def select_nth(page, field_id, index):
    """
    Cierra dropdowns abiertos, abre el dropdown indicado,
    selecciona el item en la posicion index y cierra.
    """
    await close_any_open_dropdown(page)
    await page.wait_for_timeout(400)

    btn = page.locator(f"ngx-select-dropdown#{field_id} .ngx-dropdown-button")
    await btn.scroll_into_view_if_needed()
    await btn.click(timeout=8000)
    await page.wait_for_timeout(800)

    item = page.locator(f"ngx-select-dropdown#{field_id} .available-item").nth(index)
    await item.scroll_into_view_if_needed()
    await item.click(timeout=8000)
    await page.wait_for_timeout(600)


async def read_options_from_open(page, field_id) -> list[str]:
    """Abre el dropdown y lee las opciones sin seleccionar ninguna."""
    await close_any_open_dropdown(page)
    await page.wait_for_timeout(400)

    btn = page.locator(f"ngx-select-dropdown#{field_id} .ngx-dropdown-button")
    await btn.scroll_into_view_if_needed()
    await btn.click(timeout=8000)
    await page.wait_for_timeout(800)

    options = await get_options(page, field_id)
    await close_any_open_dropdown(page)
    return options


async def fetch_all_routes(credentials: dict) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        ok = await login(page, credentials)
        if not ok:
            await browser.close()
            return {}

        await go_to_transport(page)
        await page.wait_for_selector("client-ticket-reserve", timeout=10000)

        # Preparar formulario base
        await page.locator("#EntradaySalida").check()
        await page.wait_for_timeout(500)
        await page.locator("#reserve_date").fill("2026-03-17")
        await page.wait_for_timeout(1000)

        # ── LLEGADA: leer todas las rutas ──────────────────────────────
        arrival_routes = await read_options_from_open(page, "time_in")
        print(f"\n📋 Rutas de llegada: {len(arrival_routes)}")

        # ── LLEGADA: por cada ruta obtener sus paradas ─────────────────
        arrival_stops = {}
        for i, route in enumerate(arrival_routes):
            print(f"  🔍 [{i+1}/{len(arrival_routes)}] {route}")
            try:
                await select_nth(page, "time_in", i)

                if await wait_enabled(page, "stop_in"):
                    stops = await read_options_from_open(page, "stop_in")
                    arrival_stops[route] = stops
                    print(f"     ✅ {len(stops)} paradas")
                else:
                    arrival_stops[route] = []
                    print(f"     ⚠️  stop_in no se habilitó")

            except Exception as e:
                print(f"     ❌ {e}")
                arrival_stops[route] = []
                await close_any_open_dropdown(page)

        # ── SALIDA: necesitamos time_in + stop_in seleccionados ────────
        # Dejar la primera ruta de llegada y primera parada seleccionadas
        print("\n🔧 Preparando formulario para rutas de salida...")
        await select_nth(page, "time_in", 0)
        await wait_enabled(page, "stop_in")
        await select_nth(page, "stop_in", 0)
        await wait_enabled(page, "time_out")
        await page.wait_for_timeout(500)

        # ── SALIDA: leer todas las rutas ───────────────────────────────
        departure_routes = await read_options_from_open(page, "time_out")
        print(f"\n📋 Rutas de salida: {len(departure_routes)}")

        # ── SALIDA: por cada ruta obtener sus paradas ──────────────────
        departure_stops = {}
        for i, route in enumerate(departure_routes):
            print(f"  🔍 [{i+1}/{len(departure_routes)}] {route}")
            try:
                await select_nth(page, "time_out", i)

                if await wait_enabled(page, "stop_out"):
                    stops = await read_options_from_open(page, "stop_out")
                    departure_stops[route] = stops
                    print(f"     ✅ {len(stops)} paradas")
                else:
                    departure_stops[route] = []
                    print(f"     ⚠️  stop_out no se habilitó")

            except Exception as e:
                print(f"     ❌ {e}")
                departure_stops[route] = []
                await close_any_open_dropdown(page)

            # Mantener stop_in seleccionado para que time_out siga habilitado
            # (no resetear el formulario entre iteraciones de salida)

        await browser.close()

        return {
            "arrival": {
                "routes": arrival_routes,
                "stops_by_route": arrival_stops,
            },
            "departure": {
                "routes": departure_routes,
                "stops_by_route": departure_stops,
            }
        }


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()

    credentials = {
        "email": "",
        "password": "",
    }

    async def main():
        print("🚀 Extrayendo rutas y paradas...\n")
        data = await fetch_all_routes(credentials)

        output_path = Path(__file__).parent / "routes.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Resumen
        print("\n" + "="*55)
        print("  RUTAS DE LLEGADA")
        print("="*55)
        for route, stops in data["arrival"]["stops_by_route"].items():
            print(f"\n  🟢 {route}")
            for stop in stops:
                print(f"      • {stop}")

        print("\n" + "="*55)
        print("  RUTAS DE SALIDA")
        print("="*55)
        for route, stops in data["departure"]["stops_by_route"].items():
            print(f"\n  🔴 {route}")
            for stop in stops:
                print(f"      • {stop}")

        print(f"\n✅ Guardado en {output_path}")

    asyncio.run(main())