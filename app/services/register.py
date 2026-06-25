from infrastructure.database import get_session
from infrastructure.repository.user import UserRepository
from utils.encryption import encrypt


async def register_user(user_id: int, email: str, password: str) -> bool:

    session = get_session()

    try:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_user_id(user_id)

        encrypted_password = await encrypt(password)

        if user is None:
            await user_repo.create(user_id, email, encrypted_password)
            return True

        else:
            await user_repo.update(
                user_id,
                email,
                encrypted_password,
            )
            return False

    except Exception as e:
        raise ValueError("Hubo un error registrando al usuario", e)

    finally:
        session.close()
