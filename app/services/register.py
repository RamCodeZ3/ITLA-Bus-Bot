from infrastructure.repository.user import UserRepository
from infrastructure.database import get_session


async def register_user(
    discord_id: int,
    email: str,
    password: str
    ) -> bool:
    
    session = get_session()
    
    try:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_discord_id(discord_id)
    
        if user is None:
            await user_repo.create(
                discord_id,
                email,
                password # directo sin encriptar
            )
            return True

        else:
            await user_repo.update(
                discord_id,
                email,
                password,
            )
            return False
    
    except Exception as e:
        raise ValueError("Hubo un error registrando al usuario", e)

    finally:
        session.close()

