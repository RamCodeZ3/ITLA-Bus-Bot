import discord
from datetime import datetime, timedelta
from infrastructure.database import get_session
from infrastructure.repository.stock_history import StockHistoryRepository
from infrastructure.repository.schedule import ScheduleRepository
from scraper.scrapper_ticket import ITLAScraper
from models.ticket_model import TicketModel


class TicketView(discord.ui.View):
    def __init__(self, user_data: dict, bot):
        super().__init__(timeout=None)
        self.user_data = user_data
        self.bot = bot

    @discord.ui.button(
        label="🎫 Comprar Ticket",
        style=discord.ButtonStyle.success,
    )
    async def buy(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.disable_all()
        await interaction.response.edit_message(
            content="✅ Procesando tu compra...",
            view=self,
        )
        tomorrow = datetime.now() + timedelta(days=1)
        day_name = tomorrow.strftime("%A").lower()
        session = get_session()

        schedule_repo = ScheduleRepository(session)
        schedule = schedule_repo.get_schedule_by_id_and_day(
            interaction.user.id,
            day_name
        )

        await self._buy_tickets(interaction.user.id, schedule)

        session = get_session()
        stock_repo = StockHistoryRepository(session)
        stock_repo.create(
            user_id=interaction.user.id,
            schedule_day_id=schedule["schedule_day_id"],
            date= datetime.now().date(),
            status="bought",
        )

    @discord.ui.button(
        label="❌ No comprar",
        style=discord.ButtonStyle.danger,
    )
    async def decline(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.disable_all()
        await interaction.response.edit_message(
            content="👍 Entendido, no se comprará ticket.",
            embed=None,
            view=self,
        )
        tomorrow = datetime.now() + timedelta(days=1)
        day_name = tomorrow.strftime("%A").lower()

        schedule_repo = ScheduleRepository(session)
        schedule = schedule_repo.get_schedule_by_id_and_day(
            interaction.user.id,
            day_name
        )

        session = get_session()
        stock_repo = StockHistoryRepository(session)
        stock_repo.create(
            user_id=interaction.user.id,
            schedule_day_id=schedule["schedule_day_id"],
            date= datetime.now().date(),
            status="refused",
        )

    def disable_all(self):
        for item in self.children:
            item.disabled = True
    
    async def _buy_tickets(self, discord_id: int, schedule_day: dict):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        tickets = TicketModel(
            date=tomorrow,
            arrival_route=schedule_day["arrival_route"],
            pickup_stop=schedule_day["pickup_stop"],
            departure_route=schedule_day["departure_route"],
            dropoff_stop=schedule_day["dropoff_stop"]
        )

        try:
            user = await self.bot.fetch_user(discord_id)
        except discord.NotFound:
            print(f"Usuario {discord_id} no encontrado")
            return

        scraper = ITLAScraper(discord_id, tickets)
        result = await scraper.run()


        if not result["success"]:
            await user.send(
                f"❌ No se pudo comprar los boletos de mañana **{tomorrow}**. "
                f" {result['error']}"
            )
            return

        tickets: list[dict] = result["data"]

        files = [
            discord.File(fp=ticket["buffer"], filename=ticket["filename"])
            for ticket in tickets
        ]

        await user.send(
            content=(
                f"✅ ¡Boletos comprados para mañana **{tomorrow}**!\n"
                f" Hora de llegada: **{schedule_day['arrival_route']}**\n"
                f" Hora de salida: **{schedule_day['departure_route']}**"
            ),
            files=files
        )
