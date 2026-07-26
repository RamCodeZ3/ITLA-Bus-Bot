from playwright.async_api import TimeoutError, async_playwright

from utils.responses import ok, error

URL_CAMPUS="https://campusvirtual.itla.edu.do/account/login"

class ItlaAuth:
    async def run(self, email: str, password: str):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-images",
                        "--blink-settings=imagesEnabled=false"
                    ],
                )
                
                context = await browser.new_context()
                await context.route(
                    "**/*",
                    lambda route: route.abort()
                    if route.request.resource_type in [
                        "image",
                        "stylesheet",
                        "font",
                        "media"
                    ]
                    else route.continue_()
                )

                page = await context.new_page()

                await page.goto(URL_CAMPUS)
                await page.wait_for_load_state("networkidle")

                await page.locator("#email").fill(email)
                await page.locator("#password").fill(password)
                await page.get_by_role("button", name="Iniciar Sesión").click()
                await page.wait_for_load_state("networkidle")

                try:
                    await page.wait_for_selector(
                        ".btn-logout, button:has-text('Salir')", timeout=5000
                    )
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

                return ok(True)

        except TimeoutError as t:
            raise ValueError(f"Hubo un tiempo de espera agotado autenticando al usuario: {t}")
        except Exception as e:
            return error(f"Error inesperado autenticando al usuario: {e}")

itla_auth = ItlaAuth()
