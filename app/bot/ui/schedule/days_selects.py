import discord
from ui.schedule.page_view import ScheduleState
from ui.schedule.routes_selects import ArrivalRouteSelect
from utils.schedule_utils import ALL_DAYS, DAYS_ES, day_embed


class DaysSelectView(discord.ui.View):
    def __init__(self, state: ScheduleState):
        super().__init__(timeout=300)
        self.state = state

    @discord.ui.button(
        label="Lunes",
        style=discord.ButtonStyle.secondary,
        custom_id="monday",
    )
    async def monday(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_day(interaction, button, "monday")

    @discord.ui.button(
        label="Martes",
        style=discord.ButtonStyle.secondary,
        custom_id="tuesday",
    )
    async def tuesday(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_day(interaction, button, "tuesday")

    @discord.ui.button(
        label="Miércoles",
        style=discord.ButtonStyle.secondary,
        custom_id="wednesday",
    )
    async def wednesday(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_day(interaction, button, "wednesday")

    @discord.ui.button(
        label="Jueves",
        style=discord.ButtonStyle.secondary,
        custom_id="thursday",
    )
    async def thursday(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_day(interaction, button, "thursday")

    @discord.ui.button(
        label="Viernes",
        style=discord.ButtonStyle.secondary,
        custom_id="friday",
    )
    async def friday(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_day(interaction, button, "friday")

    @discord.ui.button(
        label="Sábado",
        style=discord.ButtonStyle.secondary,
        custom_id="saturday",
        row=1,
    )
    async def saturday(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        await self.toggle_day(interaction, button, "saturday")

    @discord.ui.button(
        label="✅ Confirmar días",
        style=discord.ButtonStyle.success,
        row=1,
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if not self.state.selected_days:
            await interaction.response.send_message(
                "⚠️ Debes seleccionar al menos un día.",
                ephemeral=True,
            )
            return

        self.state.selected_days.sort(key=lambda d: ALL_DAYS.index(d))
        first_day = self.state.selected_days[0]
        await interaction.response.edit_message(
            embed=day_embed(first_day, 0, len(self.state.selected_days)),
            view=ArrivalRouteSelect(self.state),
        )

    async def toggle_day(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
        day: str,
    ):
        if day in self.state.selected_days:
            self.state.selected_days.remove(day)
            button.style = discord.ButtonStyle.secondary
        else:
            self.state.selected_days.append(day)
            button.style = discord.ButtonStyle.primary

        selected_text = (
            ", ".join(DAYS_ES[d] for d in self.state.selected_days)
            or "Ninguno"
        )
        embed = discord.Embed(
            title="¿Qué días vas al ITLA?",
            description=(
                "Selecciona los días y presiona **Confirmar**.\n\n"
                f"**Seleccionados:** {selected_text}"
            ),
            color=discord.Color.blurple(),
        )
        await interaction.response.edit_message(embed=embed, view=self)
