import discord
from infrastructure.database import get_session
from infrastructure.reposity import StockHistory


class TicketView(discord.ui.View):
    def __init__(self, user_data: dict):
        super().__init__(timeout=None)
        self.user_data = user_data

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
        session = get_session()
        stock_repo = StockHistory(session)

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

    def disable_all(self):
        for item in self.children:
            item.disabled = True
