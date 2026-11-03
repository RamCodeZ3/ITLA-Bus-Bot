"""Reservations list, payment dialog and ticket image dialog."""

import base64
import re
import struct
from datetime import date, datetime

from playwright.async_api import Locator

from app.domain.exceptions import TicketError
from app.domain.models import TicketImage
from app.infrastructure.scraper.pages.base import BasePage

# Intercept the portal's generated image before the browser download layer.
# Both data URLs and blob URLs are read in the page, never into temp files.
CAPTURE_IMAGES = r"""
(() => {
    window.__ticketImages = [];
    window.__ticketCaptureError = false;
    const blobs = new Map();
    const createURL = URL.createObjectURL.bind(URL);
    const revokeURL = URL.revokeObjectURL.bind(URL);
    URL.createObjectURL = blob => {
        const url = createURL(blob); blobs.set(url, blob); return url;
    };
    URL.revokeObjectURL = url => { blobs.delete(url); revokeURL(url); };
    const capture = async (anchor) => {
        try {
            if (anchor.href.startsWith('data:image/')) {
                window.__ticketImages.push(anchor.href); return;
            }
            const blob = blobs.get(anchor.href) ||
                await (await fetch(anchor.href)).blob();
            const reader = new FileReader();
            reader.onload = () => window.__ticketImages.push(reader.result);
            reader.onerror = () => window.__ticketCaptureError = true;
            reader.readAsDataURL(blob);
        } catch (_) { window.__ticketCaptureError = true; }
    };
    const isImage = a => a && (a.download ||
        a.href.startsWith('blob:') || a.href.startsWith('data:image/'));
    const original = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function(...args) {
        if (isImage(this)) { void capture(this); return; }
        return original.apply(this, args);
    };
    const dispatch = HTMLAnchorElement.prototype.dispatchEvent;
    HTMLAnchorElement.prototype.dispatchEvent = function(event) {
        if (event.type === 'click' && isImage(this)) {
            void capture(this); return false;
        }
        return dispatch.call(this, event);
    };
    document.addEventListener('click', event => {
        const anchor = event.target.closest?.('a');
        if (isImage(anchor)) {
            event.preventDefault(); event.stopImmediatePropagation();
            void capture(anchor);
        }
    }, true);
})();
"""


def validate_image(data: bytes) -> None:
    """Reject invalid PNG headers and the known one-pixel placeholder."""
    if len(data) < 33 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise TicketError("INVALID_TICKET_IMAGE", "Invalid ticket PNG.")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 1 or height <= 1:
        raise TicketError("INVALID_TICKET_IMAGE", "Empty ticket PNG.")


class ReservationsPage(BasePage):
    """Operate on unambiguous reservation rows without retrying payments."""

    _URL = "https://transporte.itla.edu.do/customers/reservas"
    _ROWS = "tr.datatable-row"
    _QR = "plantilla-qr a.btn-light-primary"
    _PAY = "a.btn-light-success"

    async def open(self) -> None:
        """Wait for rows or an explicit empty-state indicator."""
        await self.navigate(self._URL)
        await self.page.locator(
            "tr.datatable-row, .datatable-empty, .empty-row, "
            "td.dataTables_empty"
        ).first.wait_for()

    async def row_for_date(self, day: date) -> Locator | None:
        """Require one matching reservation to avoid paying the wrong row."""
        label = day.strftime("%d-%m-%Y")
        rows = self.page.locator(self._ROWS).filter(
            has=self.page.locator("td").filter(
                has_text=re.compile(rf"^\s*{re.escape(label)}\s*$")
            )
        )
        count = await rows.count()
        if count > 1:
            raise TicketError(
                "AMBIGUOUS_RESERVATION",
                "Multiple reservations match the date. Verify Campus.",
                409,
            )
        return rows.first if count else None

    async def assert_not_reserved(self, day: date) -> None:
        """Reject an existing reservation before creating or paying again."""
        if await self.row_for_date(day) is not None:
            raise TicketError(
                "RESERVATION_EXISTS",
                "A reservation exists. Retrieve tickets or verify Campus.",
                409,
            )

    async def purchase(self, day: date) -> None:
        """Submit a payment once and require a purchased-ticket control."""
        row = await self.row_for_date(day)
        if row is None:
            raise TicketError(
                "RESERVATION_NOT_FOUND", "Reservation was not confirmed.", 409
            )
        await row.locator(self._PAY).click()
        await self.page.locator(".swal2-popup").wait_for()
        # No retry is allowed once this call starts: payment may have happened.
        try:
            await self.page.locator("button.swal2-confirm").click()
            await row.locator(self._PAY).wait_for(state="hidden")
            await row.locator(self._QR).wait_for(state="visible")
        except Exception:
            raise TicketError(
                "PURCHASE_OUTCOME_UNKNOWN",
                "Payment outcome is unknown. Retrieve before retrying.",
                502,
            ) from None

    async def first_usable_date(self, today: date) -> date | None:
        """Select the first purchased row usable today or in the future."""
        rows = self.page.locator(self._ROWS)
        for index in range(await rows.count()):
            row = rows.nth(index)
            if not await row.locator(self._QR).count():
                continue
            match = re.search(r"\b\d{2}-\d{2}-\d{4}\b", await row.inner_text())
            if match:
                day = datetime.strptime(match[0], "%d-%m-%Y").date()
                if day >= today:
                    return day
        return None

    async def images(self, day: date) -> list[TicketImage]:
        """Read every available direction without initiating file downloads."""
        result = []
        for direction, value in (("entry", "1"), ("exit", "0")):
            row = await self.row_for_date(day)
            if row is None:
                return result
            await row.locator(self._QR).click()
            await self.page.locator("div.swal2-popup").wait_for()
            radio = self.page.locator(
                f"div.swal2-radio input[name='swal2-radio'][value='{value}']"
            )
            if (
                not await radio.count()
                or not await radio.is_visible()
                or not await radio.is_enabled()
            ):
                await self.page.keyboard.press("Escape")
                await self.page.locator("div.swal2-popup").wait_for(
                    state="hidden"
                )
                continue
            await radio.check()
            await self.page.evaluate(
                "window.__ticketImages = []; "
                "window.__ticketCaptureError = false"
            )
            await self.page.locator("button.swal2-confirm").click()
            await self.page.wait_for_function(
                "window.__ticketImages.length > 0 || "
                "window.__ticketCaptureError"
            )
            encoded = await self.page.evaluate("window.__ticketImages.shift()")
            if not encoded or not encoded.startswith("data:image/png;base64,"):
                raise TicketError(
                    "INVALID_TICKET_IMAGE", "Image capture failed."
                )
            data = base64.b64decode(encoded.split(",", 1)[1], validate=True)
            validate_image(data)
            identifier = f"{day.isoformat()}-{direction}"
            result.append(TicketImage(identifier, f"{identifier}.png", data))
            await self.page.locator("div.swal2-popup").wait_for(state="hidden")
        return result
