import discord
from discord import app_commands
from discord.ext import commands

from services.schedule import ScheduleService, DAYS_ES


class ScheduleDay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="get-schedule",
        description="Comando para mostrar el horario del cuatrimestre actual.",
    )
    async def get_schedule_command(self, interaction: discord.Interaction):
        await interaction.response.defer()

        schedule_repo = ScheduleService()

        schedule_days = await schedule_repo.get_schedule_days(
            interaction.user.id
        )

        if not schedule_days:
            await interaction.followup.send(
                "❌ No tienes un horario activo o días programados",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📅 Tu Horario del Cuatrimestre",
            description="Aquí tienes tu horario completa de rutas",
            color=discord.Color.darker_gray(),
        )

        for day in schedule_days:
            day_lower_case = day.day.lower()
            spanish_day = DAYS_ES.get(day_lower_case, day.day.capitalize())

            info_routes = (
                f"**Entrada (Ruta):** {day.arrival_route}\n"
                f"**Parada:** {day.pickup_stop}\n"
                f"**Salida (Ruta):** {day.departure_route}"
            )

            embed.add_field(
                name=f"**{spanish_day}**", value=info_routes, inline=False
            )

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ScheduleDay(bot))
