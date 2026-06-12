from datetime import datetime

from infrastructure.database import get_session
from infrastructure.repository.stock_history import StockHistoryRepository
from infrastructure.repository.user import UserRepository


NEXT_DAY_MAP = {
    0: "tuesday",
    1: "wednesday",
    2: "thursday",
    3: "friday",
    4: "saturday",
    6: "monday",
}

DAYS_ES = {
    "monday": "lunes",
    "tuesday": "martes",
    "wednesday": "miércoles",
    "thursday": "jueves",
    "friday": "viernes",
    "saturday": "sábado",
}

TASK_HOUR = 11
TASK_MINUTE = 0


class SchedulerTask:

    def __init__(self) -> None:
        self.last_notified_date = None
    
    async def daily_check(self):
        now = datetime.now()

        if now.weekday() not in NEXT_DAY_MAP:
            return

        if now.hour != TASK_HOUR or now.minute != TASK_MINUTE:
            if now.hour < TASK_HOUR:
                self.last_notified_date = None
            return

        today = now.date()
        if self.last_notified_date == today:
            return

        self.last_notified_date = today
        tomorrow_day = NEXT_DAY_MAP[now.weekday()]

        await self.notify_users(tomorrow_day)

    async def catchup_check(self):
        now = datetime.now()
        today = now.date()

        if now.weekday() not in NEXT_DAY_MAP:
            return

        if not (TASK_HOUR <= now.hour < 17):
            return

        if self.last_notified_date == today:
            return

        self.last_notified_date = today
        tomorrow_day = NEXT_DAY_MAP[now.weekday()]

        return tomorrow_day
    
    async def notify_users(self, day: str):
        session = get_session()
        user_repo = UserRepository(session)
        stock_repo = StockHistoryRepository(session)
        users_to_notify = []

        try:
            users = user_repo.get_users_with_day(day)
            today = datetime.now().date()

            for user_data in users:
                # Verificar si ya existe un StockHistory para este
                # schedule_day en la fecha de mañana
                already_notified = stock_repo.get_by_schedule_day_and_date(
                    schedule_day_id=user_data["schedule_day_id"], date=today
                )
                if already_notified and already_notified.status != "failed":
                    continue

                users_to_notify.append(user_data)

        except Exception as e:
            raise ValueError("Hubo un errror notificando a los usuarios", e)

        finally:
            return users_to_notify
