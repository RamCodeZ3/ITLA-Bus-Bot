import discord
from discord.ext import commands
from discord import app_commands
from db.reposity import UserRepository, ScheduleRepository
from db.database import get_session
from data.routes_data import ROUTES_DATA


WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
ALL_DAYS = WEEKDAYS + ["saturday"]
DAYS_ES = {
    "monday": "Lunes",
    "tuesday": "Martes",
    "wednesday": "Miércoles",
    "thursday": "Jueves",
    "friday": "Viernes",
    "saturday": "Sábado",
}
MAX_OPTIONS = 25


def get_routes_for_day(day: str) -> dict:
    if day == "saturday":
        return ROUTES_DATA["saturday"]
    else:
        return ROUTES_DATA["weekday"]


def truncate(text: str, max_len: int = 97) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def total_pages(items: list) -> int:
    return max(1, -(-len(items) // MAX_OPTIONS))


def build_options(items: list[str], page: int) -> list[discord.SelectOption]:
    start = page * MAX_OPTIONS
    return [
        discord.SelectOption(label=truncate(item), value=truncate(item, 100))
        for item in items[start: start + MAX_OPTIONS]
    ]


class ScheduleState:
    def __init__(self, term: str):
        self.term = term
        self.selected_days: list[str] = []
        self.current_day_index: int = 0
        self.days_data: dict = {}


class PagedView(discord.ui.View):
    """View base con Select paginado."""

    def __init__(self, state: ScheduleState, placeholder: str, page: int = 0):
        super().__init__(timeout=300)
        self.state = state
        self.placeholder = placeholder
        self.page = page
        self._render()

    def get_items(self) -> list[str]:
        raise NotImplementedError

    async def on_select(self, interaction: discord.Interaction, value: str):
        raise NotImplementedError

    def _render(self):
        self.clear_items()
        items = self.get_items()
        pages = total_pages(items)
        options = build_options(items, self.page)

        select = discord.ui.Select(
            placeholder=f"{self.placeholder} ({self.page + 1}/{pages})",
            options=options,
        )

        async def _callback(interaction: discord.Interaction):
            await self.on_select(interaction, interaction.data["values"][0])

        select.callback = _callback
        self.add_item(select)

        if self.page > 0:
            btn = discord.ui.Button(
                label="◀ Anterior",
                style=discord.ButtonStyle.secondary,
                row=1,
            )
            btn.callback = self._prev
            self.add_item(btn)

        if self.page < pages - 1:
            btn = discord.ui.Button(
                label="Siguiente ▶",
                style=discord.ButtonStyle.secondary,
                row=1,
            )
            btn.callback = self._next
            self.add_item(btn)

    async def _prev(self, interaction: discord.Interaction):
        self.page -= 1
        self._render()
        await interaction.response.edit_message(view=self)

    async def _next(self, interaction: discord.Interaction):
        self.page += 1
        self._render()
        await interaction.response.edit_message(view=self)


class DepartureStopSelect(PagedView):
    def __init__(self, state: ScheduleState, page: int = 0):
        super().__init__(state, "Parada de bajada (salida)", page)

    def get_items(self) -> list[str]:
        day = self.state.selected_days[self.state.current_day_index]
        route = self.state.days_data[day]["departure_route"]
        routes_data = get_routes_for_day(day)["departure"]["stops_by_route"]
        stops = routes_data.get(route, [])
        return stops or ["Única parada"]

    async def on_select(self, interaction: discord.Interaction, value: str):
        day = self.state.selected_days[self.state.current_day_index]
        self.state.days_data[day]["dropoff_stop"] = value
        self.state.current_day_index += 1

        if self.state.current_day_index < len(self.state.selected_days):
            next_day = self.state.selected_days[self.state.current_day_index]
            await interaction.response.edit_message(
                embed=day_embed(
                    next_day,
                    self.state.current_day_index,
                    len(self.state.selected_days),
                ),
                view=ArrivalRouteSelect(self.state),
            )
        else:
            await save_schedule(interaction, self.state)


class DepartureRouteSelect(PagedView):
    def __init__(self, state: ScheduleState, page: int = 0):
        super().__init__(state, "Ruta de salida (regreso)", page)

    def get_items(self) -> list[str]:
        day = self.state.selected_days[self.state.current_day_index]
        return get_routes_for_day(day)["departure"]["routes"]

    async def on_select(self, interaction: discord.Interaction, value: str):
        day = self.state.selected_days[self.state.current_day_index]
        self.state.days_data[day]["departure_route"] = value
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Parada de bajada (salida)",
                description=(
                    f"**{DAYS_ES[day]}** "
                    "— ¿En qué parada te bajas al regresar?"
                ),
                color=discord.Color.orange(),
            ),
            view=DepartureStopSelect(self.state),
        )


class ArrivalStopSelect(PagedView):
    def __init__(self, state: ScheduleState, page: int = 0):
        super().__init__(state, "Parada de subida (llegada)", page)

    def get_items(self) -> list[str]:
        day = self.state.selected_days[self.state.current_day_index]
        route = self.state.days_data[day]["arrival_route"]
        routes_data = get_routes_for_day(day)["arrival"]["stops_by_route"]
        stops = routes_data.get(route, [])
        return stops or ["Única parada"]

    async def on_select(self, interaction: discord.Interaction, value: str):
        day = self.state.selected_days[self.state.current_day_index]
        self.state.days_data[day]["pickup_stop"] = value
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Ruta de salida (regreso)",
                description=(
                    f"**{DAYS_ES[day]}** — ¿En qué ruta regresas a casa?"
                ),
                color=discord.Color.orange(),
            ),
            view=DepartureRouteSelect(self.state),
        )


class ArrivalRouteSelect(PagedView):
    def __init__(self, state: ScheduleState, page: int = 0):
        super().__init__(state, "Ruta de llegada al ITLA", page)

    def get_items(self) -> list[str]:
        day = self.state.selected_days[self.state.current_day_index]
        return get_routes_for_day(day)["arrival"]["routes"]

    async def on_select(self, interaction: discord.Interaction, value: str):
        day = self.state.selected_days[self.state.current_day_index]
        self.state.days_data[day] = {
            "arrival_route": value,
            "pickup_stop": None,
            "departure_route": None,
            "dropoff_stop": None,
        }
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="🚏 Parada de subida (llegada)",
                description=(
                    f"**{DAYS_ES[day]}** — ¿En qué parada subes al bus?"
                ),
                color=discord.Color.blue(),
            ),
            view=ArrivalStopSelect(self.state),
        )


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
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(
            embed=embed,
            view=DaysSelectView(state),
            ephemeral=True,
        )


def day_embed(day: str, index: int, total: int) -> discord.Embed:
    tipo = "sábado" if day == "saturday" else "día de semana"
    return discord.Embed(
        title=f"🚌 Ruta de llegada — {DAYS_ES[day]}",
        description=(
            f"Día {index + 1} de {total} ({tipo})\n\n"
            "¿En qué ruta llegas al ITLA?"
        ),
        color=discord.Color.blue(),
    )


async def save_schedule(
    interaction: discord.Interaction,
    state: ScheduleState,
):
    session = get_session()
    try:
        user_repo = UserRepository(session)
        schedule_repo = ScheduleRepository(session)

        user = user_repo.get_by_discord_id(interaction.user.id)
        if not user:
            await interaction.response.edit_message(
                content="❌ No estás registrado. Usa `/register` primero.",
                embed=None,
                view=None,
            )
            return

        schedule = schedule_repo.create(user_id=user.id, term=state.term)

        for day, data in state.days_data.items():
            from models.schedule_days import ScheduleDays
            schedule_repo.add_day(
                ScheduleDays(
                    schedule_id=schedule.id,
                    day=day,
                    ticket_type="round_trip",
                    arrival_route=data["arrival_route"],
                    pickup_stop=data["pickup_stop"],
                    departure_route=data["departure_route"],
                    dropoff_stop=data["dropoff_stop"],
                )
            )

        days_list = "\n".join(
            f"• **{DAYS_ES[d]}** — "
            f"🟢 {v['arrival_route']} → 🔴 {v['departure_route']}"
            for d, v in state.days_data.items()
        )
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ Horario configurado",
                description=f"**Período:** {state.term}\n\n{days_list}",
                color=discord.Color.green(),
            ),
            view=None,
        )
    except Exception as e:
        print(f"Error guardando horario: {e}")
        await interaction.response.edit_message(
            content="❌ Ocurrió un error al guardar tu horario.",
            embed=None,
            view=None,
        )
    finally:
        session.close()


class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="schedule",
        description=(
            "Configura los días y rutas de transporte"
            " para el período académico"
        ),
    )
    async def configurar_horario(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TermModal())


async def setup(bot):
    await bot.add_cog(Schedule(bot))
