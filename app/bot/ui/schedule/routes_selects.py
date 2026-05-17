import discord
from ui.schedule.page_view import PagedView, ScheduleState
from utils.schedule_utils import (
    DAYS_ES,
    day_embed,
    get_routes_for_day,
    save_schedule,
)


class DepartureRouteSelect(PagedView):
    def __init__(self, state: ScheduleState, page: int = 0):
        super().__init__(state, "Hora de Salida del ITLA", page)

    def get_items(self) -> list[str]:
        day = self.state.selected_days[self.state.current_day_index]
        return get_routes_for_day(day)["departure"]["routes"]

    async def on_select(self, interaction: discord.Interaction, value: str):
        day = self.state.selected_days[self.state.current_day_index]
        self.state.days_data[day]["departure_route"] = value
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


class ArrivalStopSelect(PagedView):
    def __init__(self, state: ScheduleState, page: int = 0):
        super().__init__(state, "Parada de subida al bus", page)

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
                color=discord.Color.darker_gray(),
            ),
            view=DepartureRouteSelect(self.state),
        )


class ArrivalRouteSelect(PagedView):
    def __init__(self, state: ScheduleState, page: int = 0):
        super().__init__(state, "Hora de Llegada al ITLA", page)

    def get_items(self) -> list[str]:
        day = self.state.selected_days[self.state.current_day_index]
        return get_routes_for_day(day)["arrival"]["routes"]

    async def on_select(self, interaction: discord.Interaction, value: str):
        day = self.state.selected_days[self.state.current_day_index]
        self.state.days_data[day] = {
            "arrival_route": value,
            "pickup_stop": None,
            "departure_route": None,
        }
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Parada de subida al bus",
                description=(
                    f"**{DAYS_ES[day]}** — ¿En qué parada subes al bus?"
                ),
                color=discord.Color.darker_gray(),
            ),
            view=ArrivalStopSelect(self.state),
        )
