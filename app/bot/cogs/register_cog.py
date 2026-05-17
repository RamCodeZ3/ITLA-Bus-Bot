import discord
from discord import app_commands
from discord.ext import commands
from infrastructure.database import get_session
from infrastructure.repository.user import UserRepository


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
            user = repository.get_by_discord_id(interaction.user.id)

            if user is None:
                repository.create(
                    discord_id=interaction.user.id,
                    email=email,
                    password=password,  # Directo sin encriptar
                )
                embed = discord.Embed(
                    title="✅ Registro Exitoso",
                    description=(
                        "Te registraste de manera exitosa."
                        "Aquí están tus credenciales:"
                    ),
                    color=discord.Color.darker_gray(),
                )
                embed.add_field(name="Email", value=email, inline=False)
                embed.add_field(
                    name="Contraseña", value=password, inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                repository.update(
                    discord_id=interaction.user.id,
                    email=email,
                    password=password,
                )
                embed = discord.Embed(
                    title="✅ Credenciales Actualizadas",
                    description=(
                        "Se actualizaron tus credenciales de manera exitosa."
                        "Aquí están tus nuevas credenciales:"
                    ),
                    color=discord.Color.darker_gray(),
                )
                embed.add_field(name="Email", value=email, inline=False)
                embed.add_field(
                    name="Contraseña", value=password, inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                "❌ Ocurrió un error al registrarte.", ephemeral=True
            )
            raise ValueError(f"[Register] Error: {e}")
        finally:
            session.close()


async def setup(bot):
    await bot.add_cog(Register(bot))
