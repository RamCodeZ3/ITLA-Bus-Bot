import discord
from ui.schedule.days_selects import DaysSelectView
from ui.schedule.page_view import ScheduleState


class TermModal(discord.ui.Modal, title="Configurar Horario"):
    term = discord.ui.TextInput(
        label="Período académico",
        placeholder="Ej: 2026-1",
        min_length=4,
        max_length=10,
    )

    async def on_submit(self, interaction: discord.Interaction):
        state = ScheduleState(term=self.term.value)
        embed = discord.Embed(
            title="¿Qué días vas al ITLA?",
            description=(
                "Selecciona los días y presiona **Confirmar**.\n\n"
                "**Seleccionados:** Ninguno"
            ),
            color=discord.Color.darker_gray(),
        )
        await interaction.response.send_message(
            embed=embed,
            view=DaysSelectView(state),
            ephemeral=True,
        )
