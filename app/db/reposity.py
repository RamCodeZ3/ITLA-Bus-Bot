from sqlalchemy.orm import Session
from db.models import Purchase, Schedule, ScheduleDay, User
from models.schedule_days import ScheduleDays
from models.purchase import Purchase


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
            discord_id=discord_id,
            email=email,
            password=password
        )
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_discord_id(self, discord_id: int) -> User | None:
        return self.session.query(User).filter_by(
            discord_id=discord_id
        ).first()
    
    def get_users_with_day(self, session, day: str) -> list[dict]:

        results = (
            session.query(User, ScheduleDay)
            .join(Schedule, Schedule.user_id == User.id)
            .join(ScheduleDay, ScheduleDay.schedule_id == Schedule.id)
            .filter(Schedule.active == True)  # noqa: E712
            .filter(ScheduleDay.day == day)
            .all()
        )
        return [
            {
                "discord_id": user.discord_id,
                "day": schedule_day.day,
                "arrival_route": schedule_day.arrival_route,
                "pickup_stop": schedule_day.pickup_stop,
                "departure_route": schedule_day.departure_route,
                "dropoff_stop": schedule_day.dropoff_stop,
            }
            for user, schedule_day in results
        ]


class ScheduleRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: int, term: str) -> Schedule:
        # Deactivate previous schedules for this user
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

    def add_day(self, schedule_days: ScheduleDays) -> ScheduleDay:
        schedule_day = ScheduleDay(
            schedule_id=schedule_days.schedule_id,
            day=schedule_days.day,
            ticket_type=schedule_days.ticket_type,
            arrival_route=schedule_days.arrival_route,
            pickup_stop=schedule_days.pickup_stop,
            departure_route=schedule_days.departure_route,
            dropoff_stop=schedule_days.dropoff_stop,
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


class PurchaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, purchase: Purchase) -> Purchase:
        purchase = Purchase(
            user_id=purchase.user_id,
            date=purchase.date,
            ticket_type=purchase.ticket_type,
            arrival_route=purchase.arrival_route,
            pickup_stop=purchase.pickup_stop,
            departure_route=purchase.departure_route,
            dropoff_stop=purchase.dropoff_stop,
        )
        self.session.add(purchase)
        self.session.commit()
        self.session.refresh(purchase)
        return purchase

    def update_status(
            self,
            purchase_id: int,
            status: str,
            pdf_path: str = None
        ):
        purchase = self.session.query(Purchase).filter_by(
            id=purchase_id
        ).first()
        if purchase:
            purchase.status = status
            if pdf_path:
                purchase.pdf_path = pdf_path
            self.session.commit()

    def get_by_user(self, user_id: int) -> list[Purchase]:
        return self.session.query(Purchase).filter_by(
            user_id=user_id
        ).order_by(
            Purchase.purchased_at.desc()
        ).all()
