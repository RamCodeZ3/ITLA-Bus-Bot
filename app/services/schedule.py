from data.routes_data import ROUTES_DATA
from infrastructure.database import get_session
from infrastructure.repository.schedule import ScheduleRepository
from infrastructure.repository.user import UserRepository
from schemas.schedule_days_schema import ScheduleDaysSchema

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
ALL_DAYS = WEEKDAYS + ["saturday"]
DAYS_ES = {
    "monday": "Lunes",
    "tuesday": "Martes",
    "wednesday": "Miércoles",
    "thursday": "Jueves",
    "friday": "Viernes",
    "saturday": "Sábado",
}


def get_routes_for_day(day: str) -> dict:
    if day == "saturday":
        return ROUTES_DATA["saturday"]
    return ROUTES_DATA["weekday"]


def truncate(text: str, max_len: int = 97) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def build_schedule_summary(term: str, days_data: dict) -> str:
    days_list = "\n".join(
        f"• **{DAYS_ES[d]}** — 🟢 {v['arrival_route']} → 🔴 {v['departure_route']}"
        for d, v in days_data.items()
    )
    return f"**Período:** {term}\n\n{days_list}"


class ScheduleService:
    async def save_schedule(self, discord_user_id: int, term: str, days_data: dict) -> str:
        """
        Persists the schedule for a user.

        Returns a summary string on success.
        Raises ValueError if the user is not registered.
        Raises RuntimeError on unexpected errors.
        """
        session = get_session()
        try:
            user_repo = UserRepository(session)
            schedule_repo = ScheduleRepository(session)

            user = await user_repo.get_by_discord_id(discord_user_id)
            if not user:
                raise ValueError("user_not_registered")

            schedule = schedule_repo.create(user_id=user.id, term=term)
            for day, data in days_data.items():
                schedule_repo.add_day(
                    ScheduleDaysSchema(
                        schedule_id=schedule.id,
                        day=day,
                        ticket_type="round_trip",
                        arrival_route=data["arrival_route"],
                        pickup_stop=data["pickup_stop"],
                        departure_route=data["departure_route"],
                    )
                )

            return build_schedule_summary(term, days_data)

        except ValueError:
            raise
        except Exception as e:
            raise RuntimeError("save_failed") from e
        finally:
            session.close()
