from sqlalchemy.orm import Session
from infrastructure.models import Schedule, ScheduleDay, User
from models.schedule_days_model import ScheduleDaysModel


class ScheduleRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: int, term: str) -> Schedule:
        self.session.query(Schedule).filter_by(
            user_id=user_id,
            active=True).update(
                {"active": False}
            )
        schedule = Schedule(user_id=user_id, term=term, active=True)
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def get_active(self, user_id: int) -> Schedule | None:
        return self.session.query(Schedule).filter_by(user_id=user_id, active=True).first()

    def add_day(self, schedule_days: ScheduleDaysModel) -> ScheduleDay:
        schedule_day = ScheduleDay(
            schedule_id=schedule_days.schedule_id,
            day=schedule_days.day,
            ticket_type=schedule_days.ticket_type,
            arrival_route=schedule_days.arrival_route,
            pickup_stop=schedule_days.pickup_stop,
            departure_route=schedule_days.departure_route,
        )
        self.session.add(schedule_day)
        self.session.commit()
        self.session.refresh(schedule_day)
        return schedule_day

    def get_days(self, schedule_id: int) -> list[ScheduleDay]:
        return self.session.query(ScheduleDay).filter_by(
            schedule_id=schedule_id
        ).all()

    def get_day(self, schedule_id: int, day: str) -> ScheduleDay | None:
        return self.session.query(ScheduleDay).filter_by(
            schedule_id=schedule_id,
            day=day
        ).first()
    
    def get_schedule_by_id_and_day(self, discord_id: int, day: str) -> dict | None:
        schedule_day = (
            self.session.query(ScheduleDay)
            .join(Schedule, Schedule.id == ScheduleDay.schedule_id)
            .join(User, User.id == Schedule.user_id)
            .filter(Schedule.active == True)
            .filter(User.id == discord_id)
            .filter(ScheduleDay.day == day)
            .first()
        )

        if not schedule_day:
            return None

        return {
            "schedule_day_id": schedule_day.id,
            "day": schedule_day.day,
            "arrival_route": schedule_day.arrival_route,
            "pickup_stop": schedule_day.pickup_stop,
            "departure_route": schedule_day.departure_route,
        }
