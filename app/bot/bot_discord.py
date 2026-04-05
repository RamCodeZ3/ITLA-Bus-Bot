import discord
import os
import sys
from dotenv import load_dotenv
from discord.ext import commands


class BotITLATicket(commands.Bot):
    def __init__(self):
        load_dotenv()
        self.token = os.getenv("DISCORD_TOKEN")
        self.cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.dm_messages = True

        super().__init__(command_prefix="/", intents=intents)

    async def setup_hook(self):
        """Se ejecuta automáticamente antes de conectarse al gateway."""
        await self.load_cogs()

    async def on_ready(self):
        print(f"Bot conectado y funcionando: {self.user}")
        try:
            synced = await self.tree.sync()
            print(f"{len(synced)} Slash Commands sincronizados")
        except Exception as e:
            print(f"Error al sincronizar comandos: {e}")

    async def load_cogs(self):
        bot_dir = os.path.dirname(__file__)
        if bot_dir not in sys.path:
            sys.path.insert(0, bot_dir)

        for filename in os.listdir(self.cogs_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                except Exception as e:
                    print(f"Error cargando {cog_name}: {e}")
    
    def run_bot(self):
        self.run(self.token)
