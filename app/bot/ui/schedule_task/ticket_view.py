from datetime import datetime, timedelta

import discord
from services.ticket import Tickets


class TicketView(discord.ui.View):
    def __init__(self, user_data: dict, bot):
        super().__init__(timeout=None)
        self.user_data = user_data
        self.bot = bot
        self.tickets = Tickets(user_data["user_id"])

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
        schedule = await self.tickets.get_schedule_by_id()
        result = await self.tickets.buy_tickets()

        await self.buy_tickets(result, schedule)

        if result and not result["success"]:

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
        await self.tickets.mark_as_refused()

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
        await self.tickets.mark_as_pending()
        await interaction.response.edit_message(
            content="Se le recordada más tarde para comprar los boletos",
            embed=None,
            view=self,
        )

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

    async def buy_tickets(self, result: dict, schedule_day: dict):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            user = await self.bot.fetch_user(self.user_data["user_id"])
        except discord.NotFound:
            return None

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
        self.tickets = Tickets(user_data["user_id"])
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

        result = await self.tickets.buy_tickets()
        await ticket_view.buy_tickets(result, self.schedule)

        if result and not result["success"]:
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
        await self.tickets.mark_as_cancelled()
        await interaction.response.edit_message(
            content="🚫 Compra cancelada.",
            embed=None,
            view=self,
        )

    def disable_all(self):
        for item in self.children:
            item.disabled = True
