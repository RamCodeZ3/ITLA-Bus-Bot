import discord
from db.reposity import UserRepository, ScheduleRepository
from db.database import get_session
from data.routes_data import ROUTES_DATA
from app.models.schedule_days_model import ScheduleDaysModel


WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday"
]
ALL_DAYS = WEEKDAYS + ["saturday"]

DAYS_ES = {
    "monday": "Lunes",
    "tuesday": "Martes",
    "wednesday": "Miércoles",
    "thursday": "Jueves",
    "friday": "Viernes",
    "saturday": "Sábado",
}


def get_routes_for_day(day: str) -> dict:
    if day == "saturday":
        return ROUTES_DATA["saturday"]
    return ROUTES_DATA["weekday"]


def truncate(text: str, max_len: int = 97) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


def day_embed(day: str, index: int, total: int) -> discord.Embed:
    tipo = "sábado" if day == "saturday" else "día de semana"
    return discord.Embed(
        title=f"🚌 Ruta de llegada — {DAYS_ES[day]}",
        description=(
            f"Día {index + 1} de {total} ({tipo})\n\n"
            "¿En qué ruta llegas al ITLA?"
        ),
        color=discord.Color.blue(),
    )


async def save_schedule(
    interaction: discord.Interaction,
    state,
):
    session = get_session()
    try:
        user_repo = UserRepository(session)
        schedule_repo = ScheduleRepository(session)

        user = user_repo.get_by_discord_id(interaction.user.id)
        if not user:
            await interaction.response.edit_message(
                content="❌ No estás registrado. Usa `/register` primero.",
                embed=None,
                view=None,
            )
            return

        schedule = schedule_repo.create(user_id=user.id, term=state.term)

        for day, data in state.days_data.items():
            schedule_repo.add_day(
                ScheduleDaysModel(
                    schedule_id=schedule.id,
                    day=day,
                    ticket_type="round_trip",
                    arrival_route=data["arrival_route"],
                    pickup_stop=data["pickup_stop"],
                    departure_route=data["departure_route"],
                    dropoff_stop=data["dropoff_stop"],
                )
            )

        days_list = "\n".join(
            f"• **{DAYS_ES[d]}** — "
            f"🟢 {v['arrival_route']} → 🔴 {v['departure_route']}"
            for d, v in state.days_data.items()
        )
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ Horario configurado",
                description=f"**Período:** {state.term}\n\n{days_list}",
                color=discord.Color.green(),
            ),
            view=None,
        )
    except Exception as e:
        print(f"Error guardando horario: {e}")
        await interaction.response.edit_message(
            content="❌ Ocurrió un error al guardar tu horario.",
            embed=None,
            view=None,
        )
    finally:
        session.close()
