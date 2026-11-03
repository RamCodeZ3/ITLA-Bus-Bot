"""Framework-independent workflow failures."""


class TicketError(Exception):
    """A safe error suitable for returning to a caller."""

    def __init__(self, code: str, message: str, status: int = 502) -> None:
        self.code = code
        self.message = message
        self.status = status
        super().__init__(message)
