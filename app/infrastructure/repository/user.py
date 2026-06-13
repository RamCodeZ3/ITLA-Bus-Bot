from sqlalchemy.orm import Session

from ..models import Schedule, ScheduleDay, User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    async def create(self, user_id: int, email: str, password: str) -> User:
        user = User(id=user_id, email=email, password=password)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    async def update(
        self,
        user_id,
        email,
        password,
    ):
        user = self.session.query(User).filter_by(id=user_id).first()

        if user is None:
            return None

        user.email = email
        user.password = password

        self.session.commit()
        self.session.refresh(user)

        return user

    async def get_by_user_id(self, user_id: int) -> User | None:
        return self.session.query(User).filter_by(id=user_id).first()

    async def get_users_with_day(self, day: str) -> list[dict]:
        results = (
            self.session.query(User, ScheduleDay)
            .join(Schedule, Schedule.user_id == User.id)
            .join(ScheduleDay, ScheduleDay.schedule_id == Schedule.id)
            .filter(Schedule.active)
            .filter(ScheduleDay.day == day)
            .all()
        )
        return [
            {
                "user_id": user.id,
                "schedule_day_id": schedule_day.id,
                "day": schedule_day.day,
                "arrival_route": schedule_day.arrival_route,
                "pickup_stop": schedule_day.pickup_stop,
                "departure_route": schedule_day.departure_route,
            }
            for user, schedule_day in results
        ]

    async def get_user_data_by_schedule_day_id(
        self, schedule_day_id: int
    ) -> dict | None:
        result = (
            self.session.query(User, ScheduleDay)
            .join(Schedule, Schedule.user_id == User.id)
            .join(ScheduleDay, ScheduleDay.schedule_id == Schedule.id)
            .filter(ScheduleDay.id == schedule_day_id)
            .first()
        )
        if result is None:
            return None
        user, schedule_day = result
        return {
            "user_id": user.id,
            "schedule_day_id": schedule_day.id,
            "day": schedule_day.day,
            "arrival_route": schedule_day.arrival_route,
            "pickup_stop": schedule_day.pickup_stop,
            "departure_route": schedule_day.departure_route,
        }
