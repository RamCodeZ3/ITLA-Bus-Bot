import discord
from discord import app_commands
from discord.ext import commands

from services.register import register_user


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

        try:
            result = await register_user(interaction.user.id, email, password)
            if result["auth"] and result["type"] == "register":
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
                    name="Contraseña", value=f"||{password}||", inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

            elif result["auth"] and result["type"] == "updated":
                embed = discord.Embed(
                    title="✅ Credenciales Actualizadas",
                    description=(
                        "Se actualizaron tus credenciales de manera exitosa."
                    ),
                    color=discord.Color.darker_gray(),
                )
                embed.add_field(name="Email", value=email, inline=False)
                embed.add_field(
                    name="Contraseña", value=f"||{password}||", inline=False
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

            else:
                embed = discord.Embed(
                    title="❌ Credenciales incorrectas",
                    description=(
                        "El correo o la contraseña ingresados para el "
                        "**Campus Virtual** no son correctos.\n\n"
                        "Por favor, verifica tus datos e intenta acceder"
                        " de nuevo en el portal:\n"
                        "🔗 https://campusvirtual.itla.edu.do/account/login"
                    ),
                    color=discord.Color.darker_gray(),
                )

                embed.add_field(name="Email", value=f"`{email}`", inline=False)
                embed.add_field(
                    name="Contraseña", value=f"||{password}||", inline=False
                )

                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                "❌ Ocurrió un error al registrarte.", ephemeral=True
            )
            raise ValueError(f"[Register] Error: {e}")


async def setup(bot):
    await bot.add_cog(Register(bot))
