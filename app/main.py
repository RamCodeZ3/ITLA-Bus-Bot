from bot.bot_discord import BotITLATicket
from infrastructure.database import init_db

if __name__ == "__main__":
    init_db()

    bot = BotITLATicket()
    bot.run_bot()
