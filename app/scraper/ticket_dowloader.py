import os
from datetime import datetime
from playwright.async_api import Page, Download


class TicketDownloader:

    RADIO_VALUE_ENTRY = "1"   # Descargar ticket de entrada
    RADIO_VALUE_EXIT  = "0"   # Descargar ticket de salida

    def __init__(self, download_dir: str = "."):
        self.download_dir = os.path.abspath(download_dir)
        os.makedirs(self.download_dir, exist_ok=True)

    async def download_tickets(self, page: Page, ticket_date: str) -> list[str]:

        date_label = datetime.strptime(ticket_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        downloaded: list[str] = []

        print(f"📥  Descargando boletos para la fecha: {date_label}")

        entry_path = await self._download_one(
            page=page,
            date_label=date_label,
            radio_value=self.RADIO_VALUE_ENTRY,
            ticket_type="entrada",
            filename=f"boleto_entrada_{date_label}.png",
        )
        downloaded.append(entry_path)

        exit_path = await self._download_one(
            page=page,
            date_label=date_label,
            radio_value=self.RADIO_VALUE_EXIT,
            ticket_type="salida",
            filename=f"boleto_salida_{date_label}.png",
        )
        downloaded.append(exit_path)

        print("✅  Descarga completada:")
        for path in downloaded:
            print(f"    • {path}")

        return downloaded

    async def _download_one(
        self,
        page: Page,
        date_label: str,
        radio_value: str,
        ticket_type: str,
        filename: str,
    ) -> str:
        print(f"\n  ── Descargando boleto de {ticket_type.upper()} ──")

        await self._click_qr_button(page, date_label)
        await self._wait_for_modal(page)
        await self._select_radio(page, radio_value, ticket_type)
        path = await self._click_ok_and_save(page, filename)

        # Wait for modal to close before the next cycle
        await page.wait_for_timeout(1500)

        return path

    async def _click_qr_button(self, page: Page, date_label: str) -> None:

        row = page.locator("tr.datatable-row").filter(
            has=page.locator(f"td:has-text('{date_label}')")
        ).filter(
            has=page.locator("plantilla-qr a.btn-light-primary")  # solo existe en "Pagado"
        )
        await row.wait_for(state="visible", timeout=8000)
        await row.locator("plantilla-qr a.btn-light-primary").click()
        print(f"  ✓ Botón QR presionado para la fecha: {date_label}")

    async def _wait_for_modal(self, page: Page) -> None:
        """Waits for the SweetAlert2 download modal to be visible."""
        await page.wait_for_selector(
            "div.swal2-popup",
            state="visible",
            timeout=8000,
        )
        print("  ✓ Modal de descarga visible")

    async def _select_radio(
        self, page: Page, radio_value: str, ticket_type: str
    ) -> None:

        radio = page.locator(
            f"div.swal2-radio input[name='swal2-radio'][value='{radio_value}']"
        )
        await radio.check()
        print(f"  ✓ Opción seleccionada: {ticket_type} (value={radio_value})")

    async def _click_ok_and_save(self, page: Page, filename: str) -> str:

        dest_path = os.path.join(self.download_dir, filename)

        async with page.expect_download(timeout=15000) as download_info:
            await page.locator("button.swal2-confirm").click()
            print(f"  ✓ OK presionado — esperando descarga de '{filename}'...")

        download: Download = await download_info.value
        await download.save_as(dest_path)
        print(f"  ✓ Archivo guardado: {dest_path}")

        return dest_path
