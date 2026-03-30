from infrastructure.database import init_db
from bot.bot_discord import BotITLATicket


if __name__ == '__main__':
    init_db()

    bot = BotITLATicket()
    bot.run_bot()
