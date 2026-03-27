import discord
from discord.ext import commands, tasks
from datetime import datetime
from infrastructure.database import get_session
from infrastructure.repository.user import UserRepository
from infrastructure.repository.stock_history import StockHistoryRepository
from ui.schedule_task.ticket_view import TicketView


NEXT_DAY_MAP = {
    0: "tuesday",
    1: "wednesday",
    2: "thursday",
    3: "friday",
    4: "saturday",
    6: "monday",
}

DAYS_ES = {
    "monday": "lunes",
    "tuesday": "martes",
    "wednesday": "miércoles",
    "thursday": "jueves",
    "friday": "viernes",
    "saturday": "sábado",
}

TASK_HOUR = 15
TASK_MINUTE = 0


class SchedulerTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.last_notified_date = None
        self.daily_check.start()

    def cog_unload(self):
        self.daily_check.cancel()

    @tasks.loop(minutes=1)
    async def daily_check(self):
        now = datetime.now()

        if now.weekday() not in NEXT_DAY_MAP:
            return

        if now.hour != TASK_HOUR or now.minute != TASK_MINUTE:
            if now.hour < TASK_HOUR:
                self.last_notified_date = None
            return

        today = now.date()
        if self.last_notified_date == today:
            return

        self.last_notified_date = today
        tomorrow_day = NEXT_DAY_MAP[now.weekday()]
        await self.notify_users(tomorrow_day)

    @daily_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()
        await self._catchup_check()

    async def _catchup_check(self):
        now = datetime.now()
        today = now.date()

        if now.weekday() not in NEXT_DAY_MAP:
            return

        if not (TASK_HOUR <= now.hour < 17):
            return

        if self.last_notified_date == today:
            return

        print(
            "[SchedulerTask] Bot reiniciado despues de la hora de notificacion,"
            " enviando notificaciones pendientes..."
        )
        self.last_notified_date = today
        tomorrow_day = NEXT_DAY_MAP[now.weekday()]
        await self.notify_users(tomorrow_day)

    async def notify_users(self, day: str):
        session = get_session()
        user_repo = UserRepository(session)
        stock_repo = StockHistoryRepository(session)

        try:
            users = user_repo.get_users_with_day(day)
            today = datetime.now().date()

            print(
                f"[SchedulerTask] Notificando {len(users)} usuarios"
                f" para mañana ({DAYS_ES[day]})"
            )

            for user_data in users:
                # Verificar si ya existe un StockHistory para este
                # schedule_day en la fecha de mañana
                already_notified = stock_repo.get_by_schedule_day_and_date(
                    schedule_day_id=user_data["schedule_day_id"],
                    date=today
                )
                if already_notified:
                    print(
                        f"[SchedulerTask] Usuario {user_data['discord_id']}"
                        f" ya fue notificado hoy, omitiendo."
                    )
                    continue

                await self._send_dm(user_data, day)

        except Exception as e:
            print(f"[SchedulerTask] Error en notify_users: {e}")
        finally:
            session.close()

    async def _send_dm(self, user_data: dict, day: str):
        try:
            user = await self.bot.fetch_user(user_data["discord_id"])
            if user is None:
                return

            day_name = DAYS_ES[day]
            embed = discord.Embed(
                title=f"🚌 Recordatorio — Mañana es {day_name}",
                description=(
                    "Tienes clases mañana. "
                    "¿Deseas comprar tu ticket de transporte?"
                ),
                color=discord.Color.blue(),
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
                value=(
                    f"**Ruta:** {user_data['departure_route']}\n"
                    f"**Parada:** {user_data['dropoff_stop']}"
                ),
                inline=False,
            )
            embed.set_footer(text="ITLA Bot • Sistema de Tickets")

            await user.send(embed=embed, view=TicketView(user_data))

        except discord.Forbidden:
            print(
                f"[SchedulerTask] No se pudo enviar DM"
                f" a {user_data['discord_id']} (DMs cerrados)"
            )
        except Exception as e:
            print(
                f"[SchedulerTask] Error enviando DM"
                f" a {user_data['discord_id']}: {e}"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerTask(bot))