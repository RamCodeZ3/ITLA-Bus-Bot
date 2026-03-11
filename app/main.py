from db.database import init_db
from bot.bot_discord import BotClient


if __name__ == '__main__':
    init_db()
    bot = BotClient()
    bot.run_bot()