import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL_CAMPUS = "https://campusvirtual.itla.edu.do"
DATES = ["2026-04-27", "2026-04-28", "2026-04-29", "2026-04-30"]


# ──────────────────────────────────────────────────────────────
#  LOGIN / NAVEGACIÓN
# ──────────────────────────────────────────────────────────────

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
    print(f"✅ En página de transporte → {page.url}")


# ──────────────────────────────────────────────────────────────
#  HELPERS DE DROPDOWN
# ──────────────────────────────────────────────────────────────

async def close_any_open_dropdown(page):
    await page.keyboard.press("Escape")
    await page.wait_for_timeout(300)
    try:
        await page.locator("client-ticket-reserve").click(
            position={"x": 10, "y": 10}, timeout=1000
        )
    except Exception:
        pass
    await page.wait_for_timeout(300)


async def is_enabled(page, field_id) -> bool:
    btn = page.locator(f"ngx-select-dropdown#{field_id} .ngx-dropdown-button")
    classes = await btn.get_attribute("class") or ""
    return "ngx-disabled" not in classes


async def wait_enabled(page, field_id, timeout_ms=8000) -> bool:
    for _ in range(timeout_ms // 300):
        if await is_enabled(page, field_id):
            return True
        await page.wait_for_timeout(300)
    return False


async def get_options(page, field_id) -> list[str]:
    items = page.locator(f"ngx-select-dropdown#{field_id} .available-item")
    count = await items.count()
    return [(await items.nth(i).inner_text()).strip() for i in range(count)]


async def open_dropdown(page, field_id):
    await close_any_open_dropdown(page)
    await page.wait_for_timeout(400)
    btn = page.locator(f"ngx-select-dropdown#{field_id} .ngx-dropdown-button")
    await btn.scroll_into_view_if_needed()
    await btn.click(timeout=8000)
    await page.wait_for_timeout(800)


async def select_nth(page, field_id, index):
    await open_dropdown(page, field_id)
    item = page.locator(f"ngx-select-dropdown#{field_id} .available-item").nth(index)
    await item.scroll_into_view_if_needed()
    await item.click(timeout=8000)
    await page.wait_for_timeout(700)


async def read_all_options(page, field_id) -> list[str]:
    await open_dropdown(page, field_id)
    options = await get_options(page, field_id)
    await close_any_open_dropdown(page)
    return options


# ──────────────────────────────────────────────────────────────
#  SCRAPING POR DÍA
#
#  Por cada hora de llegada (time_in[i]):
#    → leer paradas de subida (stop_in)
#    → por cada parada (stop_in[j]):
#         → leer horas de salida disponibles (time_out)
#
#  Resultado: { hora_llegada: { parada: [horas_salida] } }
# ──────────────────────────────────────────────────────────────

async def scrape_day(page, date: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  📅 {date}")
    print(f"{'='*60}")

    await page.locator("#EntradaySalida").check()
    await page.wait_for_timeout(500)
    await page.locator("#reserve_date").fill(date)
    await page.wait_for_timeout(1200)

    arrival_hours = await read_all_options(page, "time_in")
    print(f"\n🕐 Horas de llegada ({len(arrival_hours)}): {arrival_hours}")

    result: dict[str, dict[str, list[str]]] = {}

    for i, hour_in in enumerate(arrival_hours):
        print(f"\n  ┌─ [{i+1}/{len(arrival_hours)}] Hora llegada: {hour_in}")
        result[hour_in] = {}

        try:
            await select_nth(page, "time_in", i)

            if not await wait_enabled(page, "stop_in"):
                print(f"  └─ ⚠️  stop_in no habilitado → saltando")
                continue

            stops = await read_all_options(page, "stop_in")
            print(f"  │  🚏 Paradas de subida ({len(stops)}): {stops}")

            for j, stop in enumerate(stops):
                print(f"  │    ├─ [{j+1}/{len(stops)}] Parada: {stop}")

                try:
                    # Re-seleccionar hora de llegada antes de cada parada
                    # para asegurar que stop_in esté activo
                    await select_nth(page, "time_in", i)
                    await wait_enabled(page, "stop_in")
                    await select_nth(page, "stop_in", j)

                    if not await wait_enabled(page, "time_out"):
                        print(f"  │    │  ⚠️  time_out no habilitado")
                        result[hour_in][stop] = []
                        continue

                    hours_out = await read_all_options(page, "time_out")
                    result[hour_in][stop] = hours_out
                    print(f"  │    │  🕔 Horas salida: {hours_out}")

                except Exception as e:
                    print(f"  │    │  ❌ Error parada '{stop}': {e}")
                    result[hour_in][stop] = []
                    await close_any_open_dropdown(page)

            print(f"  └─ ✅ {hour_in} completada")

        except Exception as e:
            print(f"  └─ ❌ Error hora '{hour_in}': {e}")
            await close_any_open_dropdown(page)

    return result


# ──────────────────────────────────────────────────────────────
#  COMPARACIÓN ENTRE DÍAS
# ──────────────────────────────────────────────────────────────

def compare_days(all_data: dict[str, dict]) -> dict:
    dates = list(all_data.keys())

    all_keys: set[tuple[str, str]] = set()
    for day_data in all_data.values():
        for hour_in, stops in day_data.items():
            for stop in stops:
                all_keys.add((hour_in, stop))

    report: dict[str, dict] = {}
    for hour_in, stop in sorted(all_keys):
        key = f"{hour_in} | {stop}"
        by_day: dict[str, list[str] | None] = {}

        for date in dates:
            by_day[date] = all_data[date].get(hour_in, {}).get(stop, None)

        values = [json.dumps(v, ensure_ascii=False) for v in by_day.values()]
        has_diff = len(set(values)) > 1
        missing = [d for d, v in by_day.items() if v is None]

        report[key] = {
            "has_differences": has_diff,
            "missing_in_days": missing,
            "hours_out_by_day": by_day,
        }

    return report


def print_comparison(comparison: dict):
    stable, changed = [], []
    for key, info in comparison.items():
        if info["has_differences"] or info["missing_in_days"]:
            changed.append((key, info))
        else:
            stable.append((key, info))

    print(f"\n{'='*60}")
    print(f"  ✅ COMBINACIONES ESTABLES ({len(stable)}) — iguales los 4 días")
    print(f"{'='*60}")
    for key, info in stable:
        sample = next((v for v in info["hours_out_by_day"].values() if v is not None), [])
        print(f"  🟢 {key}")
        print(f"     → Horas salida: {sample}")

    print(f"\n{'='*60}")
    print(f"  ⚠️  COMBINACIONES CON DIFERENCIAS ({len(changed)})")
    print(f"{'='*60}")
    for key, info in changed:
        print(f"\n  🔴 {key}")
        if info["missing_in_days"]:
            print(f"     ❌ No aparece en: {info['missing_in_days']}")
        for date, hours in info["hours_out_by_day"].items():
            marker = "❓" if hours is None else ("📋" if hours else "⬜")
            print(f"     {marker} {date}: {hours}")


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────

async def fetch_all_dates(credentials: dict):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        page = await browser.new_page()

        ok = await login(page, credentials)
        if not ok:
            await browser.close()
            return {}, {}

        await go_to_transport(page)
        await page.wait_for_selector("client-ticket-reserve", timeout=10000)

        all_data: dict[str, dict] = {}
        for date in DATES:
            try:
                all_data[date] = await scrape_day(page, date)
            except Exception as e:
                print(f"\n❌ Error fatal procesando {date}: {e}")
                all_data[date] = {}

        await browser.close()

    comparison = compare_days(all_data)
    return all_data, comparison


if __name__ == "__main__":
    from dotenv import load_dotenv
    import os

    load_dotenv()

    credentials = {
        "email": os.getenv("ITLA_EMAIL", "aramymussett@gmail.com"),
        "password": os.getenv("ITLA_PASSWORD", "2007344ITLA_0105@i"),
    }

    async def main():
        print("🚀 Extrayendo rutas del 27 al 30 de abril (browser visible)...\n")
        all_data, comparison = await fetch_all_dates(credentials)

        base = Path(__file__).parent

        raw_path = base / "routes_by_day.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Datos crudos  → {raw_path}")

        cmp_path = base / "routes_comparison.json"
        with open(cmp_path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, ensure_ascii=False, indent=2)
        print(f"💾 Comparación   → {cmp_path}")

        print_comparison(comparison)

    asyncio.run(main())