import discord
from utils.schedule_utils import truncate

MAX_OPTIONS = 25


class ScheduleState:
    def __init__(self, term: str):
        self.term = term
        self.selected_days: list[str] = []
        self.current_day_index: int = 0
        self.days_data: dict = {}


def total_pages(items: list) -> int:
    return max(1, -(-len(items) // MAX_OPTIONS))


def build_options(items: list[str], page: int) -> list[discord.SelectOption]:

    start = page * MAX_OPTIONS
    return [
        discord.SelectOption(label=truncate(item), value=truncate(item, 100))
        for item in items[start : start + MAX_OPTIONS]
    ]


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
