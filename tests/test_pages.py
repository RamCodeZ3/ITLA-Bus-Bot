"""Page-level verifications independent from live Campus accounts."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.exceptions import TicketError
from app.infrastructure.scraper.pages.login import LoginPage
from app.infrastructure.scraper.pages.reservations import validate_image


def test_ticket_png_validation(png):
    validate_image(png)
    with pytest.raises(TicketError):
        validate_image(b"<html>not a ticket</html>")
    with pytest.raises(TicketError):
        validate_image(png[:16] + b"\x00\x00\x00\x01" * 2 + png[24:])


async def test_login_requires_explicit_confirmation():
    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    authenticated = MagicMock(count=AsyncMock(return_value=1))
    authenticated.or_.return_value.first.wait_for = AsyncMock()
    inputs = MagicMock(fill=AsyncMock())
    rejected = MagicMock()
    page.get_by_role.return_value.click = AsyncMock()

    def locator(selector):
        if selector in ("#email", "#password"):
            return inputs
        if ".btn-logout" in selector:
            return authenticated
        return rejected

    page.locator.side_effect = locator
    await LoginPage(page).login("student", "secret")
    authenticated.or_.return_value.first.wait_for.assert_awaited_once()
    authenticated.count.return_value = 0
    with pytest.raises(TicketError) as error:
        await LoginPage(page).login("student", "secret")
    assert error.value.code == "INVALID_CREDENTIALS"


async def test_http_error_stops_login():
    page = MagicMock(goto=AsyncMock(return_value=MagicMock(status=503)))
    with pytest.raises(TicketError) as error:
        await LoginPage(page).login("student", "secret")
    assert error.value.status == 503
    page.locator.assert_not_called()


async def test_transport_checks_balance_before_reserving():
    from app.infrastructure.scraper.pages.transport import TransportPage

    page = MagicMock()
    page.locator.return_value.inner_text = AsyncMock(return_value="DOP 59.00")
    with pytest.raises(TicketError) as error:
        await TransportPage(page).verify_balance(2)
    assert error.value.code == "INSUFFICIENT_BALANCE"
    page.get_by_role.assert_not_called()


async def test_transport_preserves_normalized_matching_and_checks_ambiguity():
    from app.infrastructure.scraper.pages.transport import TransportPage

    page = MagicMock()
    dropdown = page.locator.return_value
    dropdown.locator.return_value.click = AsyncMock()
    options = dropdown.locator.return_value
    options.first.wait_for = AsyncMock()
    options.count = AsyncMock(return_value=2)
    first = MagicMock(
        inner_text=AsyncMock(return_value="Route Á (available)"),
        click=AsyncMock(),
    )
    second = MagicMock(
        inner_text=AsyncMock(return_value="Route B"), click=AsyncMock()
    )
    options.nth.side_effect = [first, second, first]
    await TransportPage(page)._select("time_in", "Route A")
    first.click.assert_awaited_once()
    second.click.assert_not_awaited()
    options.nth.side_effect = [first, second]
    with pytest.raises(TicketError) as error:
        await TransportPage(page)._select("time_in", "Route")
    assert error.value.code == "ROUTE_UNAVAILABLE"


async def test_campus_transport_navigation_requires_expected_url():
    from app.infrastructure.scraper.pages.campus import CampusPage

    page = MagicMock()
    page.locator.return_value.click = AsyncMock()
    page.wait_for_url = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    await CampusPage(page).open_transport()
    page.wait_for_url.assert_awaited_once_with("**/customers/home**")


@pytest.mark.parametrize(
    ("available", "disabled", "expected"),
    [
        ({"1", "0"}, set(), ["entry", "exit"]),
        ({"1"}, set(), ["entry"]),
        ({"0"}, set(), ["exit"]),
        ({"1", "0"}, {"0"}, ["entry"]),
        (set(), set(), []),
    ],
)
async def test_retrieval_returns_available_directions(
    png, available, disabled, expected
):
    import base64
    from datetime import date

    from app.infrastructure.scraper.pages.reservations import ReservationsPage

    page = MagicMock()
    page.keyboard.press = AsyncMock()
    page.wait_for_function = AsyncMock()
    encoded = "data:image/png;base64," + base64.b64encode(png).decode()
    page.evaluate = AsyncMock(return_value=encoded)
    modal = MagicMock(wait_for=AsyncMock())
    confirm = MagicMock(click=AsyncMock())
    radios = {
        value: MagicMock(
            count=AsyncMock(return_value=int(value in available)),
            is_visible=AsyncMock(return_value=True),
            is_enabled=AsyncMock(return_value=value not in disabled),
            check=AsyncMock(),
        )
        for value in ("1", "0")
    }

    def locator(selector):
        if selector == "div.swal2-popup":
            return modal
        if selector == "button.swal2-confirm":
            return confirm
        return radios["1" if "value='1'" in selector else "0"]

    page.locator.side_effect = locator
    row = MagicMock()
    row.locator.return_value.click = AsyncMock()
    reservations = ReservationsPage(page)
    reservations.row_for_date = AsyncMock(return_value=row)
    images = await reservations.images(date(2026, 11, 4))
    assert [image.id for image in images] == [
        f"2026-11-04-{direction}" for direction in expected
    ]
    assert all(image.data == png for image in images)
    assert confirm.click.await_count == len(expected)
    for value in ("1", "0"):
        if value not in available or value in disabled:
            radios[value].check.assert_not_awaited()
