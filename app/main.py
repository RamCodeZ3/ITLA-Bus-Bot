from infrastructure.database import init_db
from bot.bot_discord import BotITLATicket
from scraper.scrapper_ticket import ITLAScraper
from models.ticket_model import TicketModel
import asyncio


if __name__ == '__main__':
    init_db()

    tickets = TicketModel(
        date="2026-04-09",
        arrival_route="John F. Kennedy / San Vicente de Paul 8:00AM",
        pickup_stop="Plaza Galerías del Este",
        departure_route="John F. Kennedy / San Vicente de Paul 6:00PM",
    )
    scraper = ITLAScraper(1226267059478986789, tickets)
    asyncio.run(scraper.run())
    bot = BotITLATicket()
    # bot.run_bot()
