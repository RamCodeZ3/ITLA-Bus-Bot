import discord
from discord.ext import commands
from discord import app_commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="help",
        description="Comando para mostrar todos los comandos disponible"
        " que tiene el bot"
    )
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📜 Lista de comandos",
            description="Comandos que le permitira interactuar con el bot.",
            color=discord.Color.darker_gray()
        )

        embed.add_field(
            name= "**/register**",
            value=(
                "El comando **/register** se utiliza para registrate con tus \n"
                "crendeciales (correo y contraseña) del campus virtual, tambien "
                "lo puedes utiliza para actualizar las crendeciales"
            )
        )

        embed.add_field(
            name="**/set-schedule**",
            value=(
                "Este comando se utiliza para configurar tu horario de rutas del ITLA.\n"
                "**1.** Primero te mostrará un modal donde deberás ingresar el cuatrimestre "
                "en el que te encuentras (ej: `2026-1`).\n\n"
                "**2.** Luego podrás seleccionar los **días** en los que asistirás al ITLA "
                "(de lunes a sábado).\n\n"
                "**3.** Por cada día seleccionado, configurarás mediante **menús desplegables**:\n"
                "\u20031. 🕐 Hora de llegada al ITLA\n"
                "\u20032. 🚌 Parada de recogida\n"
                "\u20033. 🕓 Hora de salida del ITLA\n"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)
    

async def setup(bot):
    await bot.add_cog(Help(bot))
