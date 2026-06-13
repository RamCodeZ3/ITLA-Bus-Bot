import discord

from services.schedule import DAYS_ES, ScheduleService


def day_embed(day: str, index: int, total: int) -> discord.Embed:
    tipo = "sábado" if day == "saturday" else "día de semana"
    return discord.Embed(
        title=f"🚌 Ruta de llegada — {DAYS_ES[day]}",
        description=(
            f"Día {index + 1} de {total} ({tipo})\n\n¿En qué ruta llegas al ITLA?"
        ),
        color=discord.Color.darker_gray(),
    )


async def save_schedule(interaction: discord.Interaction, state) -> None:
    service = ScheduleService()
    try:
        summary = await service.save_schedule(
            user_id=interaction.user.id,
            term=state.term,
            days_data=state.days_data,
        )
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="✅ Horario configurado",
                description=summary,
                color=discord.Color.darker_gray(),
            ),
            view=None,
        )

    except ValueError as e:
        if str(e) == "user_not_registered":
            await interaction.response.edit_message(
                content="❌ No estás registrado. Usa `/register` primero.",
                embed=None,
                view=None,
            )

    except RuntimeError:
        await interaction.response.edit_message(
            content="❌ Ocurrió un error al guardar tu horario.",
            embed=None,
            view=None,
        )
