from datetime import datetime, timedelta

from infrastructure.database import get_session
from infrastructure.repository.schedule import ScheduleRepository
from infrastructure.repository.stock_history import StockHistoryRepository
from infrastructure.repository.user import UserRepository
from infrastructure.scraper.scrapper_ticket import ITLAScraper
from schemas.ticket_schema import TicketSchema
from utils.encryption import descrypt
from utils.responses import error


class Tickets:
    def __init__(self, user_id: int) -> None:
        self.user_id = user_id

    async def buy_tickets(self):
        session = get_session()

        schedule = await self.get_schedule_by_id()
        result = await self._buy_tickets(self.user_id, schedule)

        try:
            if result and result["success"]:
                stock_repo = StockHistoryRepository(session)
                stock_repo.create(
                    user_id=self.user_id,
                    schedule_day_id=schedule["schedule_day_id"],
                    date=datetime.now().date(),
                    status="bought",
                )
            elif result and not result["success"]:
                stock_repo = StockHistoryRepository(session)
                stock_repo.create(
                    user_id=self.user_id,
                    schedule_day_id=schedule["schedule_day_id"],
                    date=datetime.now().date(),
                    status="failed",
                )

        except Exception as e:
            raise ValueError("Hubo un error registrando los boletos: ", e)

        finally:
            session.close()
            return result

    async def _buy_tickets(self, user_id: int, schedule_day):
        try:
            tomorrow = (datetime.now() + timedelta(days=1)).strftime(
                "%Y-%m-%d"
            )

            ticket = TicketSchema(
                date=tomorrow,
                arrival_route=schedule_day["arrival_route"],
                pickup_stop=schedule_day["pickup_stop"],
                departure_route=schedule_day["departure_route"],
            )

            session = get_session()
            repo = UserRepository(session)
            user = await repo.get_by_user_id(self.user_id)
            descripted_password = await descrypt(user.password)

            if user is None:
                return error(
                    "Usuario no encontrado. Regístrate con /register"
                    "antes de comprar los boletos."
                )

            scraper = ITLAScraper(
                user_id, ticket, user.email, descripted_password
            )
            result = await scraper.run()

            return result

        except Exception as e:
            raise ValueError("Hubo un error comprando los boletos: ", e)

    async def mark_as_refused(self) -> None:
        try:
            session = get_session()
            schedule = self.get_schedule_by_id()
            stock_repo = StockHistoryRepository(session)
            stock_repo.create(
                user_id=self.user_id,
                schedule_day_id=schedule["schedule_day_id"],
                date=datetime.now().date(),
                status="refused",
            )
            session.close()

        except Exception as e:
            raise ValueError("Hubo un error calcelando la compra: ", e)

    async def mark_as_cancelled(self) -> None:
        session = get_session()
        try:
            stock_repo = StockHistoryRepository(session)
            stock_repo.create(
                user_id=self.user_id,
                schedule_day_id=self.schedule["schedule_day_id"],
                date=datetime.now().date(),
                status="cancelled",
            )
        except Exception as e:
            raise ValueError("Hubo un error cancelando la compra: ", e)

        finally:
            session.close()

    async def mark_as_pending(self) -> None:
        try:
            session = get_session()
            schedule = await self.get_schedule_by_id()
            stock_repo = StockHistoryRepository(session)
            stock_repo.create(
                user_id=self.user_id,
                schedule_day_id=schedule["schedule_day_id"],
                date=datetime.now().date(),
                status="pending",
            )
            session.close()

        except Exception as e:
            raise ValueError("Hubo un error registrando los boletos, ", e)

    async def get_schedule_by_id(self):
        session = get_session()
        try:
            tomorrow = datetime.now() + timedelta(days=1)
            day_name = tomorrow.strftime("%A").lower()

            schedule_repo = ScheduleRepository(session)
            schedule = schedule_repo.get_schedule_by_id_and_day(
                self.user_id, day_name
            )
            return schedule

        except Exception as e:
            raise ValueError("Hubo un error obteniendo el cronograma: ", e)

        finally:
            session.close()
