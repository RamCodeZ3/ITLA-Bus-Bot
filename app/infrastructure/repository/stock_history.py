from sqlalchemy.orm import Session
from ..models import StockHistory
from datetime import datetime


class StockHistoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
            self,
            user_id: int,
            schedule_day_id: int,
            date,
            status: str
        ) -> StockHistory:
        stock = StockHistory(
            user_id=user_id,
            schedule_day_id=schedule_day_id,
            date=date,
            status=status
        )
        self.session.add(stock)
        self.session.commit()
        self.session.refresh(stock)
        return stock

    def update_status(self, stock_id: int, status: str):
        stock = self.session.query(StockHistory).filter_by(id=stock_id).first()
        if stock:
            stock.status = status
            self.session.commit()

    def get_by_user(self, user_id: int) -> list[StockHistory]:
        return self.session.query(StockHistory).filter_by(
            user_id=user_id
        ).order_by(
            StockHistory.created_at.desc()
        ).all()

    def get_by_user_and_date(self, user_id: int, date) -> list[StockHistory]:
        return self.session.query(StockHistory).filter_by(
            user_id=user_id,
            date=date
        ).all()

    def get_by_schedule_day_and_date(
            self,
            schedule_day_id: int,
            date
        ) -> StockHistory | None:
        return self.session.query(StockHistory).filter_by(
            schedule_day_id=schedule_day_id,
            date=date
        ).first()

    def get_pending(self) -> list[StockHistory]:
        return self.session.query(StockHistory).filter_by(
            status="pending"
        ).order_by(
            StockHistory.date.asc()
        ).all()
    
    def get_expired_pending(self, before: datetime) -> list[StockHistory]:
        """Pendientes cuyo updated_at lleva más de 1 hora sin cambiar."""
        return (
            self.session.query(StockHistory)
            .filter(
                StockHistory.status == "pending",
                StockHistory.updated_at <= before,
            )
            .all()
        )

    def update_status(self, stock_id: int, status: str):
        stock = self.session.query(StockHistory).filter_by(id=stock_id).first()
        if stock:
            stock.status = status
            stock.updated_at = datetime.now()  # ← importante para reiniciar el timer
            self.session.commit()
