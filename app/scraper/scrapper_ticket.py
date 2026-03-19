import asyncio
import unicodedata
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os
from datetime import datetime
from ticket_dowloader import TicketDownloader


URL_CAMPUS = "https://campusvirtual.itla.edu.do"
TICKET_PRICE = 30 # pesos

load_dotenv()

class ITLAScraper:
    def __init__(self, credentials: dict, ticket: dict):
        self.credentials = credentials
        self.ticket = ticket

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            ticket_dowloader = TicketDownloader()

            ok = await self.login(page)
            if not ok:
                await browser.close()
                return

            await self.go_to_transport(page)
            balance = await self.balance_verification(page)

            if not balance:
                await browser.close()
                return
            
            await self.fill_form(page)
            await self.confirm_reserve(page)
            await self.go_to_reserve_page(page)
            await self.confirm_buy(page)
            await ticket_dowloader.download_tickets(page, self.ticket["date"])

            await browser.close()
            print("\n🎉 Done.")

    async def login(self, page):
        print("🔐 Logging in...")
        await page.goto(URL_CAMPUS)
        await page.wait_for_load_state("networkidle")

        email_input = page.locator("#email")
        await email_input.click()
        await email_input.fill(self.credentials["email"])

        password_input = page.locator("#password")
        await password_input.click()
        await password_input.fill(self.credentials["password"])

        await page.get_by_role("button", name="Iniciar Sesión").click()
        await page.wait_for_timeout(3000)
        await page.wait_for_load_state("networkidle")

        try:
            await page.wait_for_selector(
                ".btn-logout, button:has-text('Salir')", 
                timeout=5000
            )
            print("✅ Login successful")
            return True
        except Exception:
            pass

        if await page.locator("#email").count() > 0:
            await page.screenshot(path="debug_login.png")
            error = page.locator(".alert-danger, .error-msg, .invalid-feedback, .text-danger")
            if await error.count() > 0:
                print(f"  ❌ Error: {await error.first.inner_text()}")
            print("❌ fallo el login revisa las credenciales")
            return False

        print("✅ Login successful")
        return True

    async def go_to_transport(self, page):
        print("🚌 Navigating to Transport...")
        await page.locator("li.pointer a", has_text="Transporte").click()
        await page.wait_for_url("**/customers/home**", timeout=15000)
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)
        print(f"✅ Transportando a la siguiente pagina → {page.url}")

    async def balance_verification(self, page):
        try:
            balance_text = await page.locator("span", has_text="DOP").inner_text()
            balance = int(float(balance_text.replace("DOP", "").strip()))
            
            if TICKET_PRICE * 2 < balance:
                print("✅ Balance suficientes")
                return True
            else:
                print("❌ Balance insuficiente")
                return False
        
        except Exception as e:
            ValueError("Hubo un error consiguiendo el balance del usuario", e)

    async def fill_form(self, page):
        print("📝 Filling form...")
        await page.wait_for_selector("client-ticket-reserve", timeout=10000)
        await page.wait_for_selector("#reserve_date", timeout=10000)

        await page.locator(f"#{self.ticket['type']}").check()
        print(f"  ✓ Type: {self.ticket['type']}")

        await page.locator("#reserve_date").fill(self.ticket["date"])
        print(f"  ✓ Date: {self.ticket['date']}")

        await self._ngx_select(
            page,
            "time_in",
            self.ticket["arrival_route"],
            "Arrival route"
        )
        await self._ngx_select(
            page,
            "stop_in",
            self.ticket["pickup_stop"],
            "Pickup stop"
        )
        await self._ngx_select(
            page,
            "time_out",
            self.ticket["departure_route"],
            "Departure route"
        )
        await self._ngx_select(
            page,
            "stop_out",
            self.ticket["dropoff_stop"],
            "Dropoff stop"
        )

        print("✅ Formulario completado")

    async def confirm_reserve(self, page):
        print("🎟️  Confirming reservation...")
        await page.get_by_role("button", name="Reservar").click()
        await page.wait_for_timeout(3000)
        await page.screenshot(path="confirmation.png")
        print("✅ El boleto fue reservado de manera exitosa")

    async def go_to_reserve_page(self, page):
        print("🔗 Navegando a Reservas...")
        await page.locator("li#reservas_toggle a").click()
        await page.wait_for_load_state("domcontentloaded")
        print(f"✅ Navegó a → {page.url}")
    
    async def confirm_buy(self, page):
        print("🎟️  Confirmando la compra...")

        # Busca la fila con la fecha configurada en el ticket
        fecha_formateada = datetime.strptime(
            self.ticket["date"], "%Y-%m-%d"
        ).strftime("%d-%m-%Y")

        fila = page.locator("tr.datatable-row").filter(
            has=page.locator(f"td:has-text('{fecha_formateada}')")
        )
        await fila.locator("a.btn-light-success").click()
        print(f"  ✓ Click en confirmar para fecha: {fecha_formateada}")

        await page.wait_for_selector(".swal2-popup", timeout=5000)
        await page.locator("button.swal2-confirm").click()
        print("  ✓ Modal confirmado")

        await page.wait_for_timeout(2000)
        await page.screenshot(path="confirmation.png")
        print("✅ El boleto fue confirmado exitosamente")

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
        return unicodedata.normalize("NFD", s).encode(
            "ascii",
            "ignore"
        ).decode().lower()


if __name__ == "__main__":
    credentials = {
        "email": os.getenv("EMAIL"),
        "password": os.getenv("PASSWORD")
    }

    ticket = {
        "type": "EntradaySalida",  # "EntradaySalida" | "entrada" | "salida"
        "date": "2026-03-24",
        "arrival_route": "John F. Kennedy / San Vicente de Paul 8:00AM",
        "pickup_stop": "Plaza Galerías del Este",
        "departure_route": "John F. Kennedy / San Vicente de Paul 6:00PM",
        "dropoff_stop": "Metro María Montes"
    }

    scraper = ITLAScraper(credentials, ticket)
    asyncio.run(scraper.run())