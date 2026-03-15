import discord
from discord.ext import commands
from discord import app_commands
from ui.schedule.modal import TermModal


class Schedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="set-schedule",
        description=(
            "Configura los días y rutas de transporte"
            " para el período académico"
        ),
    )
    async def setting_shedule(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TermModal())


async def setup(bot):
    await bot.add_cog(Schedule(bot))
