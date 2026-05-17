import discord
from datetime import datetime, timedelta
from infrastructure.database import get_session
from infrastructure.repository.stock_history import StockHistoryRepository
from infrastructure.repository.schedule import ScheduleRepository
from scraper.scrapper_ticket import ITLAScraper
from schemas.ticket_schema import TicketSchema


class TicketView(discord.ui.View):
    def __init__(self, user_data: dict, bot):
        super().__init__(timeout=None)
        self.user_data = user_data
        self.bot = bot

    @discord.ui.button(
        label="🎫 Comprar boletos",
        style=discord.ButtonStyle.success,
    )
    async def buy(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.disable_all()
        await interaction.response.edit_message(
            content="⏳ Procesando tu compra...",
            embed=None,
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
        session.close()

        result = await self._buy_tickets(interaction.user.id, schedule)

        if result and result["success"]:
            session = get_session()
            stock_repo = StockHistoryRepository(session)
            stock_repo.create(
                user_id=interaction.user.id,
                schedule_day_id=schedule["schedule_day_id"],
                date=datetime.now().date(),
                status="bought",
            )
            session.close()
        elif result and not result["success"]:
            session = get_session()
            stock_repo = StockHistoryRepository(session)
            stock_repo.create(
                user_id=interaction.user.id,
                schedule_day_id=schedule["schedule_day_id"],
                date=datetime.now().date(),
                status="failed",
            )
            session.close()

            try:
                user = await self.bot.fetch_user(interaction.user.id)
                error_embed = self._build_error_embed(result["error"])
                retry_view = RetryView(self.user_data, self.bot, schedule)
                await user.send(embed=error_embed, view=retry_view)
            except discord.Forbidden:
                pass

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
            content="👍 Entendido, no se comprarán los boletos de mañana.",
            embed=None,
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
        stock_repo = StockHistoryRepository(session)
        stock_repo.create(
            user_id=interaction.user.id,
            schedule_day_id=schedule["schedule_day_id"],
            date=datetime.now().date(),
            status="refused",
        )
        session.close()
    
    @discord.ui.button(
        label="⏱️ Preguntar más tarde",
        style=discord.ButtonStyle.gray,
    )
    async def later(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.disable_all()
        await interaction.response.edit_message(
            content="Se le recordada más tarde para comprar los boletos",
            embed=None,
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
        stock_repo = StockHistoryRepository(session)
        stock_repo.create(
            user_id=interaction.user.id,
            schedule_day_id=schedule["schedule_day_id"],
            date=datetime.now().date(),
            status="pending",
        )
        session.close()

    def disable_all(self):
        for item in self.children:
            item.disabled = True

    def _build_error_embed(self, error_message: str) -> discord.Embed:
        embed = discord.Embed(
            title="❌ Error al comprar los boletos",
            description=(
                "Ocurrió un problema al intentar comprar tus boletos. "
                "¿Deseas intentarlo de nuevo?"
            ),
            color=discord.Color.red(),
        )
        embed.add_field(
            name="⚠️ Motivo",
            value=error_message or "Error desconocido.",
            inline=False,
        )
        embed.set_footer(text="ITLA Bot • Sistema de Boletos")
        return embed

    async def _buy_tickets(self, discord_id: int, schedule_day: dict):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        ticket = TicketSchema(
            date=tomorrow,
            arrival_route=schedule_day["arrival_route"],
            pickup_stop=schedule_day["pickup_stop"],
            departure_route=schedule_day["departure_route"],
        )

        try:
            user = await self.bot.fetch_user(discord_id)
        except discord.NotFound:
            return None

        scraper = ITLAScraper(discord_id, ticket)
        result = await scraper.run()

        if not result["success"]:
            return result

        tickets: list[dict] = result["data"]["tickets"]
        balance: int = result["data"]["balance"]
        files = [
            discord.File(fp=t["buffer"], filename=t["filename"])
            for t in tickets
        ]
        await user.send(
            content=(
                f"✅ ¡Boletos comprados para mañana **{tomorrow}**!\n"
                f"🟢 Ruta de llegada: **{schedule_day['arrival_route']}**\n"
                f"🔴 Ruta de salida: **{schedule_day['departure_route']}**\n"
                f"💰 Tu balance actual es de: **RD${balance}**"
            ),
            files=files,
        )
        return result


class RetryView(discord.ui.View):
    def __init__(self, user_data: dict, bot, schedule: dict):
        super().__init__(timeout=None)
        self.user_data = user_data
        self.bot = bot
        self.schedule = schedule

    @discord.ui.button(
        label="🔄 Intentar de nuevo",
        style=discord.ButtonStyle.success,
    )
    async def retry(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.disable_all()
        await interaction.response.edit_message(
            content="⏳ Reintentando la compra...",
            embed=None,
            view=self,
        )

        ticket_view = TicketView(self.user_data, self.bot)
        result = await ticket_view._buy_tickets(
            interaction.user.id, self.schedule
        )

        if result and result["success"]:
            session = get_session()
            stock_repo = StockHistoryRepository(session)
            stock_repo.create(
                user_id=interaction.user.id,
                schedule_day_id=self.schedule["schedule_day_id"],
                date=datetime.now().date(),
                status="bought",
            )
            session.close()
        elif result and not result["success"]:
            try:
                user = await self.bot.fetch_user(interaction.user.id)
                error_embed = ticket_view._build_error_embed(result["error"])
                await user.send(
                    embed=error_embed,
                    view=RetryView(self.user_data, self.bot, self.schedule),
                )
            except discord.Forbidden:
                pass

    @discord.ui.button(
        label="❌ Cancelar",
        style=discord.ButtonStyle.danger,
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.disable_all()
        await interaction.response.edit_message(
            content="🚫 Compra cancelada.",
            embed=None,
            view=self,
        )

        session = get_session()
        stock_repo = StockHistoryRepository(session)
        stock_repo.create(
            user_id=interaction.user.id,
            schedule_day_id=self.schedule["schedule_day_id"],
            date=datetime.now().date(),
            status="cancelled",
        )
        session.close()

    def disable_all(self):
        for item in self.children:
            item.disabled = True
