import discord
from discord.ext import commands
from discord import app_commands
from infrastructure.repository.user import UserRepository
from infrastructure.database import get_session


class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="register",
        description="Comando para registrar el usuario con"
        "sus credenciales del campus ITLA"
    )
    async def register_command(
        self,
        interaction: discord.Interaction,
        email: str,
        password: str
    ):
        try:
            session = get_session()
            
            repository = UserRepository(session)
            repository.create(
                email=email,
                discord_id=interaction.user.id,
                password=password  # directo sin encriptar
            )

            await interaction.response.send_message(
                "Te registraste de manera exitosa", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "Ocurrió un error al registrarte",
                ephemeral=True
            )
            print(f"Error en register: {e}")
        finally:
            session.close()


async def setup(bot):
    await bot.add_cog(Register(bot))