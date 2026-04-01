import unicodedata
from playwright.async_api import async_playwright
from datetime import datetime
from .ticket_dowloader import TicketDownloader
from infrastructure.database import get_session
from infrastructure.repository.user import UserRepository
from models.ticket_model import TicketModel


URL_CAMPUS = "https://campusvirtual.itla.edu.do"
TICKET_PRICE = 30  # pesos


def ok(data=None):
    return {"success": True, "data": data, "error": None}


def error(message: str):
    return {"success": False, "data": None, "error": message}


class ITLAScraper:
    def __init__(self, discord_id: int, ticket: TicketModel):
        self.discord_id = discord_id
        self.ticket = ticket

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()
            ticket_downloader = TicketDownloader()

            steps = [
                self.login(page),
                self.go_to_transport(page),
                self.balance_verification(page),
                self.fill_form(page),
                self.confirm_reserve(page),
                self.go_to_reserve_page(page),
                # self.confirm_buy(page),
            ]

            for step in steps:
                result = await step
                if not result["success"]:
                    await browser.close()
                    return result
            
            input()
            tickets = await ticket_downloader.download_tickets(
                page, self.ticket.date
            )
            await browser.close()
            return ok(tickets)

    async def login(self, page):
        print("🔐 Iniciando sesión...")
        try:
            session = get_session()
            repo = UserRepository(session)
            user = repo.get_by_discord_id(self.discord_id)

            if user is None:
                return error(
                    "Usuario no encontrado. Regístrate con /register"
                    "antes de comprar un ticket."
                )

            await page.goto(URL_CAMPUS)
            await page.wait_for_load_state("networkidle")

            await page.locator("#email").fill(user.email)
            await page.locator("#password").fill(user.password)
            await page.get_by_role("button", name="Iniciar Sesión").click()
            await page.wait_for_timeout(3000)
            await page.wait_for_load_state("networkidle")

            try:
                await page.wait_for_selector(
                    ".btn-logout, button:has-text('Salir')",
                    timeout=5000
                )
                print("✅ Sesión iniciada")
                return ok()
            except Exception:
                pass

            if await page.locator("#email").count() > 0:
                err = page.locator(
                    ".alert-danger, .error-msg, .invalid-feedback, .text-danger"
                )
                if await err.count() > 0:
                    msg = await err.first.inner_text()
                    return error(f"Login fallido: {msg.strip()}")
                return error("Login fallido. Verifica tu correo y contraseña.")

            print("✅ Sesión iniciada")
            return ok()

        except Exception as e:
            return error(f"Error inesperado en login: {e}")

    async def go_to_transport(self, page):
        print("🚌 Navegando a Transporte...")
        try:
            await page.locator("li.pointer a", has_text="Transporte").click()
            await page.wait_for_url("**/customers/home**", timeout=15000)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(2000)
            print(f"✅ En transporte → {page.url}")
            return ok()
        except:
            return error(f"No se pudo acceder a Transporte")

    async def balance_verification(self, page):
        try:
            balance_text = await page.locator(
                "span", has_text="DOP"
            ).inner_text()
            balance = int(float(balance_text.replace("DOP", "").strip()))

            if balance >= TICKET_PRICE * 2:
                print(f"✅ Balance suficiente: RD${balance}")
                return ok(balance)

            return error(
                f"Balance insuficiente. Tienes RD${balance}, "
                f"necesitas RD${TICKET_PRICE * 2}."
            )
        except:
            return error(f"No se pudo verificar el balance")

    async def fill_form(self, page):
        print("📝 Llenando formulario...")
        try:
            await page.wait_for_selector("client-ticket-reserve", timeout=10000)
            await page.wait_for_selector("#reserve_date", timeout=10000)

            await page.locator("#EntradaySalida").check()
            await page.locator("#reserve_date").fill(self.ticket.date)

            await self._ngx_select(
                page, "time_in", "Ruta de llegada", self.ticket.arrival_route 
            )
            await self._ngx_select(
                page, "stop_in", "Parada de recogida", self.ticket.pickup_stop
            )
            await self._ngx_select(
                page, "time_out", "Ruta de salida", self.ticket.departure_route
            )
            await self._ngx_select(
                page, "stop_out", "Parada de bajada"
            )

            print("✅ Formulario completado")
            return ok()
        except:
            return error(f"Error al llenar el formulario")

    async def confirm_reserve(self, page):
        print("🎟️ Confirmando reserva...")
        try:
            await page.get_by_role("button", name="Reservar").click()
            await page.wait_for_timeout(3000)
            print("✅ Reserva realizada")
            return ok()
        except:
            return error(f"No se pudo reservar el ticket")

    async def go_to_reserve_page(self, page):
        print("🔗 Navegando a Reservas...")
        try:
            await page.goto("https://transporte.itla.edu.do/customers/reservas")
            return ok()
        except:
            return error(f"No se pudo navegar a Reservas")

    async def confirm_buy(self, page):
        print("💳 Confirmando compra...")
        try:
            fecha = datetime.strptime(
                self.ticket.date, "%Y-%m-%d"
            ).strftime("%d-%m-%Y")

            fila = page.locator("tr.datatable-row").filter(
                has=page.locator(f"td:has-text('{fecha}')")
            )
            await fila.locator("a.btn-light-success").click()

            await page.wait_for_selector(".swal2-popup", timeout=5000)
            await page.locator("button.swal2-confirm").click()

            await page.wait_for_timeout(2000)
            print("✅ Compra confirmada")
            return ok()
        except:
            return error(f"No se pudo confirmar la compra")

    async def _ngx_select(self, page, field_id, field_name, search_text=None):
        selector = f"ngx-select-dropdown#{field_id}"
        await page.locator(f"{selector} .ngx-dropdown-button").click()
        await page.wait_for_timeout(1000)

        options = page.locator(f"{selector} .available-item")
        count = await options.count()

        if count == 0:
            print(f"  ⚠️ Dropdown no abrió: {field_name}")
            await page.keyboard.press("Escape")
            return
        
        if count == 1:
            text = await options.first.inner_text()
            await options.first.click()
            return

        query = self._normalize(search_text)
        for i in range(count):
            text = await options.nth(i).inner_text()
            if query in self._normalize(text):
                await options.nth(i).click()
                print(f"  ✓ {field_name}: {text.strip()}")
                return

        print(f"  ⚠️ '{search_text}' no encontrado en {field_name}:")
        for i in range(min(count, 15)):
            print(f"      [{i}] {(await options.nth(i).inner_text()).strip()}")
        await page.keyboard.press("Escape")

    @staticmethod
    def _normalize(s):
        return (
            unicodedata.normalize("NFD", s)
            .encode("ascii", "ignore")
            .decode()
            .lower()
        )
