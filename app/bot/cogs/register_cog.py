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
        description="Comando para registrar el usuario con "
        "sus credenciales del campus ITLA",
    )
    async def register_command(
        self,
        interaction: discord.Interaction,
        email: str,
        password: str,
    ):
        await interaction.response.defer(ephemeral=True)

        session = get_session()
        try:
            repository = UserRepository(session)
            repository.create(
                discord_id=interaction.user.id,
                email=email,
                password=password, # Directo sin encriptar
            )
            await interaction.followup.send(
                "✅ Te registraste de manera exitosa.", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                "❌ Ocurrió un error al registrarte.", ephemeral=True
            )
            print(f"[Register] Error: {e}")
        finally:
            session.close()


async def setup(bot):
    await bot.add_cog(Register(bot))