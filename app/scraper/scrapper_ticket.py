import asyncio
import unicodedata
from playwright.async_api import async_playwright


URL_CAMPUS = "https://campusvirtual.itla.edu.do"


class ITLAScraper:
    def __init__(self, credentials: dict, ticket: dict = None):
        self.credentials = credentials
        self.ticket = ticket

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            ok = await self.login(page)
            if not ok:
                await browser.close()
                return

            await self.go_to_transport(page)
            await self.fill_form(page)

            print("\n⏸️  Review the browser. Press ENTER to confirm...")
            input()

            await self.confirm(page)
            await browser.close()
            print("\n🎉 Done.")

    async def fetch_routes(self) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()

            ok = await self.login(page)
            if not ok:
                await browser.close()
                return {}

            await self.go_to_transport(page)
            await page.wait_for_selector("client-ticket-reserve", timeout=10000)

            # Paso 1 — habilitar time_in y time_out
            await page.locator("#EntradaySalida").check()
            await page.wait_for_timeout(500)
            await page.locator("#reserve_date").fill("2026-03-17")
            await page.wait_for_timeout(1000)

            # Paso 2 — extraer rutas de llegada
            time_in_options = await self._get_dropdown_options(page, "time_in")

            # Paso 3 — seleccionar la primera ruta de llegada para habilitar stop_in
            await page.locator("ngx-select-dropdown#time_in .ngx-dropdown-button").click()
            await page.wait_for_timeout(500)
            await page.locator("ngx-select-dropdown#time_in .available-item").first.click()
            await page.wait_for_timeout(500)

            stop_in_options = await self._get_dropdown_options(page, "stop_in")

            # Paso 4 — extraer rutas de salida
            time_out_options = await self._get_dropdown_options(page, "time_out")

            # Paso 5 — seleccionar la primera ruta de salida para habilitar stop_out
            await page.locator("ngx-select-dropdown#time_out .ngx-dropdown-button").click()
            await page.wait_for_timeout(500)
            await page.locator("ngx-select-dropdown#time_out .available-item").first.click()
            await page.wait_for_timeout(500)

            stop_out_options = await self._get_dropdown_options(page, "stop_out")

            await browser.close()
            return {
                "time_in": time_in_options,
                "stop_in": stop_in_options,
                "time_out": time_out_options,
                "stop_out": stop_out_options,
            }

    async def login(self, page):
        print("🔐 Logging in...")
        await page.goto(URL_CAMPUS)
        await page.wait_for_load_state("networkidle")

        email_input = page.locator("#email")
        await email_input.click()
        await page.keyboard.type(self.credentials["email"], delay=50)

        password_input = page.locator("#password")
        await password_input.click()
        await page.keyboard.type(self.credentials["password"], delay=50)

        await page.get_by_role("button", name="Iniciar Sesión").click()
        await page.wait_for_timeout(3000)
        await page.wait_for_load_state("networkidle")

        try:
            await page.wait_for_selector(".btn-logout, button:has-text('Salir')", timeout=5000)
            print("✅ Login successful")
            return True
        except Exception:
            pass

        if await page.locator("#email").count() > 0:
            await page.screenshot(path="debug_login.png")
            error = page.locator(".alert-danger, .error-msg, .invalid-feedback, .text-danger")
            if await error.count() > 0:
                print(f"  ❌ Error: {await error.first.inner_text()}")
            print("❌ Login failed — check debug_login.png")
            return False

        print("✅ Login successful")
        return True

    async def go_to_transport(self, page):
        print("🚌 Navigating to Transport...")
        await page.locator("li.pointer a", has_text="Transporte").click()
        await page.wait_for_url("**/customers/home**", timeout=15000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)
        print(f"✅ On transport page → {page.url}")

    async def fill_form(self, page):
        print("📝 Filling form...")
        await page.wait_for_selector("client-ticket-reserve", timeout=10000)
        await page.wait_for_selector("#reserve_date", timeout=10000)

        await page.locator(f"#{self.ticket['type']}").check()
        print(f"  ✓ Type: {self.ticket['type']}")

        await page.locator("#reserve_date").fill(self.ticket["date"])
        print(f"  ✓ Date: {self.ticket['date']}")

        await self._ngx_select(page, "time_in", self.ticket["arrival_route"], "Arrival route")
        await self._ngx_select(page, "stop_in", self.ticket["pickup_stop"], "Pickup stop")
        await self._ngx_select(page, "time_out", self.ticket["departure_route"], "Departure route")
        await self._ngx_select(page, "stop_out", self.ticket["dropoff_stop"], "Dropoff stop")

        print("✅ Form completed")

    async def confirm(self, page):
        print("🚀 Submitting reservation...")
        await page.get_by_role("button", name="Reservar").click()
        await page.wait_for_load_state("networkidle")
        await page.screenshot(path="confirmation.png")  # debug
        print("✅ Done — screenshot saved to confirmation.png")

    async def _get_dropdown_options(self, page, field_id: str) -> list[str]:
        """Opens a ngx-select-dropdown and returns all available option texts."""
        await page.locator(f"ngx-select-dropdown#{field_id} .ngx-dropdown-button").click()
        await page.wait_for_timeout(1000)

        options = page.locator(f"ngx-select-dropdown#{field_id} .available-item")
        count = await options.count()

        result = []
        for i in range(count):
            text = await options.nth(i).inner_text()
            result.append(text.strip())

        # Close dropdown
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        return result

    async def _ngx_select(self, page, field_id, search_text, field_name):
        await page.locator(f"ngx-select-dropdown#{field_id} .ngx-dropdown-button").click()
        await page.wait_for_timeout(1000)

        options = page.locator(f"ngx-select-dropdown#{field_id} .available-item")
        count = await options.count()

        if count == 0:
            print(f"  ⚠️  Dropdown did not open: {field_name}")
            await page.keyboard.press("Escape")
            return

        query = self._normalize(search_text)
        for i in range(count):
            text = await options.nth(i).inner_text()
            if query in self._normalize(text):
                await options.nth(i).click()
                print(f"  ✓ {field_name}: {text.strip()}")
                return

        print(f"  ⚠️  '{search_text}' not found in {field_name}. Available options:")
        for i in range(min(count, 15)):
            print(f"      [{i}] {(await options.nth(i).inner_text()).strip()}")
        await page.keyboard.press("Escape")

    @staticmethod
    def _normalize(s):
        return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


if __name__ == "__main__":
    credentials = {
        "email": "",
        "password": ""
    }

    async def main():
        scraper = ITLAScraper(credentials)
        routes = await scraper.fetch_routes()

        for field, options in routes.items():
            print(f"\n=== {field} ===")
            for i, option in enumerate(options):
                print(f"  [{i}] {option}")

    asyncio.run(main())