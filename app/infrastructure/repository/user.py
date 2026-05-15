from sqlalchemy.orm import Session
from ..models import User, Schedule, ScheduleDay


class UserRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def create(
            self,
            discord_id: int,
            email: str,
            password: str
        ) -> User:
        user = User(
            id= discord_id,
            email=email,
            password=password
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def update(
            self,
            discord_id,
            email,
            password,
        ):
        user = self.session.query(User).filter_by(id=discord_id).first()

        if user is None:
            return None
        
        user.email = email
        user.password = password

        self.session.commit()
        self.session.refresh(user)

        return user

    def get_by_discord_id(self, discord_id: int) -> User | None:
        return self.session.query(User).filter_by(
            id=discord_id
        ).first()
    
    def get_users_with_day(self, day: str) -> list[dict]:
        results = (
            self.session.query(User, ScheduleDay)
            .join(Schedule, Schedule.user_id == User.id)
            .join(ScheduleDay, ScheduleDay.schedule_id == Schedule.id)
            .filter(Schedule.active == True)
            .filter(ScheduleDay.day == day)
            .all()
        )
        return [
            {
                "discord_id": user.id,
                "schedule_day_id": schedule_day.id,
                "day": schedule_day.day,
                "arrival_route": schedule_day.arrival_route,
                "pickup_stop": schedule_day.pickup_stop,
                "departure_route": schedule_day.departure_route,
            }
            for user, schedule_day in results
        ]
    
    def get_user_data_by_schedule_day_id(
        self,
        schedule_day_id: int
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
            "discord_id": user.id,
            "schedule_day_id": schedule_day.id,
            "day": schedule_day.day,
            "arrival_route": schedule_day.arrival_route,
            "pickup_stop": schedule_day.pickup_stop,
            "departure_route": schedule_day.departure_route,
        }
