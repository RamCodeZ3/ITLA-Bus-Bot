from datetime import datetime, timedelta
from typing import Dict

from app.bot.cogs.remider_task_cog import REMINDER_DELAY_HOURS
from infrastructure.repository.user import UserRepository
from infrastructure.repository.stock_history import StockHistoryRepository
from infrastructure.database import get_session

REMINDER_DELAY_HOURS = 1


async def reminder_check():
    session = get_session()
    stock_repo = StockHistoryRepository(session)
    user_repo = UserRepository(session)

    users_data = []

    try:
        now = datetime.now()
        pending = stock_repo.get_expired_pending(
            before=now - timedelta(hours=REMINDER_DELAY_HOURS)
        )

        for record in pending:
            user_data = user_repo.get_user_data_by_schedule_day_id(
                record.schedule_day_id
            )
            if user_data is None:
                continue
            users_data.append(user_data)
            stock_repo.update_status(record.id, "reminded")

    except Exception as e:
        print(f"[ReminderTask] Error: {e}")
    
    finally:
        session.close()
        return users_data
