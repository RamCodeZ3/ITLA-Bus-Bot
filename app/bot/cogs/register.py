import discord
import bcrypt
from discord.ext import commands
from discord import app_commands
from db.reposity import UserRepository
from db.database import get_session


class Register(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="register",
        description="Comando para registrar el usuario con sus credenciales del campus ITLA"
    )
    async def register_command(
        self,
        interaction: discord.Interaction,
        email: str,
        password: str
    ):
        try:
            session = get_session()
        
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)
            
            repository = UserRepository(session)
            repository.create(
                email=email,
                discord_id=interaction.user.id,
                encrypted_password=hashed_password.decode("utf-8")
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
