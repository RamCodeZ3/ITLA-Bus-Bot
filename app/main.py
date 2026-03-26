import asyncio
from db.database import init_db
from bot.bot_discord import BotITLATicket
from scraper.scrapper_ticket import ITLAScraper
from models.ticket_model import TicketModel



if __name__ == '__main__':
    init_db()

    # scrapper = ITLAScraper(discord id, ticket)
    # asyncio.run(scrapper.run())

    bot = BotITLATicket()
    bot.run_bot()
