import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from infrastructure.database import get_session
from infrastructure.repository.stock_history import StockHistoryRepository
from infrastructure.repository.user import UserRepository
from ui.schedule_task.ticket_view import TicketView


REMINDER_DELAY_HOURS = 1


class ReminderTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_check.start()

    def cog_unload(self):
        self.reminder_check.cancel()

    @tasks.loop(minutes=1)
    async def reminder_check(self):
        session = get_session()
        stock_repo = StockHistoryRepository(session)
        user_repo = UserRepository(session)

        try:
            now = datetime.now()
            pending = stock_repo.get_expired_pending(
                before=now - timedelta(hours=REMINDER_DELAY_HOURS)
            )

            for record in pending:
                user_data = user_repo.get_user_data_by_schedule_day_id(
                    record.schedule_day_id
                )
                if user_data is None:
                    continue

                stock_repo.update_status(record.id, "reminded")
                await self._send_reminder(user_data)

        except Exception as e:
            print(f"[ReminderTask] Error: {e}")
        finally:
            session.close()

    @reminder_check.before_loop
    async def before_reminder_check(self):
        await self.bot.wait_until_ready()

    async def _send_reminder(self, user_data: dict):
        try:
            user = await self.bot.fetch_user(user_data["discord_id"])
            if user is None:
                return

            embed = discord.Embed(
                title="⏰ Recordatorio — Boletos pendientes",
                description=(
                    "Hace 1 hora dejaste la compra pendiente. "
                    "¿Deseas completarla ahora?"
                ),
                color=discord.Color.darker_gray(),
            )
            embed.add_field(
                name="🟢 Llegada",
                value=(
                    f"**Ruta:** {user_data['arrival_route']}\n"
                    f"**Parada:** {user_data['pickup_stop']}"
                ),
                inline=False,
            )
            embed.add_field(
                name="🔴 Salida",
                value=f"**Ruta:** {user_data['departure_route']}",
                inline=False,
            )
            embed.set_footer(text="ITLA Bot • Sistema de Boletos")

            await user.send(embed=embed, view=TicketView(user_data, self.bot))

        except discord.Forbidden:
            print(f"[ReminderTask] DMs cerrados para {user_data['discord_id']}")
        except Exception as e:
            print(f"[ReminderTask] Error enviando reminder a {user_data['discord_id']}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(ReminderTask(bot))
