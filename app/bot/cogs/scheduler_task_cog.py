import discord
from discord.ext import commands, tasks
from services.scheduler_task import SchedulerTask
from ui.schedule_task.ticket_view import TicketView

DAYS_ES = {
    "monday": "lunes",
    "tuesday": "martes",
    "wednesday": "miércoles",
    "thursday": "jueves",
    "friday": "viernes",
    "saturday": "sábado",
}

scheduler_task = SchedulerTask()


class SchedulerTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_notified_date = None
        self._daily_check.start()

    def cog_unload(self):
        self._daily_check.cancel()

    @tasks.loop(minutes=1)
    async def _daily_check(self):
        tomorrow_day = await scheduler_task.daily_check()
        await self.notify_users(str(tomorrow_day))

    @_daily_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()
        await self._catchup_check()

    async def _catchup_check(self):
        tomorrow_day = await scheduler_task.catchup_check()
        await self.notify_users(str(tomorrow_day))

    async def notify_users(self, day: str):
        try:
            users = await scheduler_task.notify_users(day)

            for user in users:
                await self._send_dm(user, day)

        except Exception as e:
            print(f"[SchedulerTask] Error en notify_users: {e}")

    async def _send_dm(self, user_data: dict, day: str):
        try:
            user = await self.bot.fetch_user(user_data["user_id"])
            if user is None:
                return

            day_name = DAYS_ES[day]
            embed = discord.Embed(
                title=f"🚌 Recordatorio — Mañana es {day_name}",
                description=(
                    "Tienes clases mañana. ¿Deseas comprar tus boletos de transporte?"
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
                value=(f"**Ruta:** {user_data['departure_route']}\n"),
                inline=False,
            )
            embed.set_footer(text="ITLA Bot • Sistema de Boletos")

            await user.send(embed=embed, view=TicketView(user_data, self.bot))

        except discord.Forbidden:
            print(
                f"[SchedulerTask] No se pudo enviar DM"
                f" a {user_data['user_id']} (DMs cerrados)"
            )
        except Exception as e:
            print(
                f"[SchedulerTask] Error enviando DM a {user_data['user_id']}: {e}"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerTaskCog(bot))
