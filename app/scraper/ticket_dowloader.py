import io
from datetime import datetime
from playwright.async_api import Page, Download


class TicketDownloader:

    RADIO_VALUE_ENTRY = "1"   # Descargar ticket de entrada
    RADIO_VALUE_EXIT  = "0"   # Descargar ticket de salida

    async def download_tickets(self, page: Page, ticket_date: str) -> list[dict]:

        date_label = datetime.strptime(ticket_date, "%Y-%m-%d").strftime("%d-%m-%Y")
        downloaded: list[dict] = []

        print(f"📥  Descargando boletos para la fecha: {date_label}")

        entry_result = await self._download_one(
            page=page,
            date_label=date_label,
            radio_value=self.RADIO_VALUE_ENTRY,
            ticket_type="entrada",
            filename=f"boleto_entrada_{date_label}.png",
        )
        downloaded.append(entry_result)

        exit_result = await self._download_one(
            page=page,
            date_label=date_label,
            radio_value=self.RADIO_VALUE_EXIT,
            ticket_type="salida",
            filename=f"boleto_salida_{date_label}.png",
        )
        downloaded.append(exit_result)

        print("✅  Descarga completada:")
        for result in downloaded:
            print(f"    • {result['filename']} ({result['buffer'].getbuffer().nbytes} bytes)")

        return downloaded

    async def _download_one(
        self,
        page: Page,
        date_label: str,
        radio_value: str,
        ticket_type: str,
        filename: str,
    ) -> dict:
        print(f"\n  ── Descargando boleto de {ticket_type.upper()} ──")

        await self._click_qr_button(page, date_label)
        await self._wait_for_modal(page)
        await self._select_radio(page, radio_value, ticket_type)
        buffer = await self._click_ok_and_load(page, filename)

        await page.wait_for_timeout(1500)

        return {"filename": filename, "ticket_type": ticket_type, "buffer": buffer}

    async def _click_qr_button(self, page: Page, date_label: str) -> None:
        row = page.locator("tr.datatable-row").filter(
            has=page.locator(f"td:has-text('{date_label}')")
        ).filter(
            has=page.locator("plantilla-qr a.btn-light-primary")
        )
        await row.wait_for(state="visible", timeout=8000)
        await row.locator("plantilla-qr a.btn-light-primary").click()
        print(f"  ✓ Botón QR presionado para la fecha: {date_label}")

    async def _wait_for_modal(self, page: Page) -> None:
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

    async def _click_ok_and_load(self, page: Page, filename: str) -> io.BytesIO:

        async with page.expect_download(timeout=15000) as download_info:
            await page.locator("button.swal2-confirm").click()
            print(f"  ✓ OK presionado — esperando descarga de '{filename}'...")

        download: Download = await download_info.value

        # Leer el stream directamente a memoria
        stream = await download.path()
        with open(stream, "rb") as f:
            buffer = io.BytesIO(f.read())

        buffer.seek(0)
        print(f"  ✓ Archivo cargado en memoria: '{filename}'")

        return buffer