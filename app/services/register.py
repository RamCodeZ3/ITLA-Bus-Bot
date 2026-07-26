from infrastructure.database import get_session
from infrastructure.repository.user import UserRepository
from utils.encryption import encrypt
from .authentication import itla_auth


async def register_user(user_id: int, email: str, password: str) -> dict:

    session = get_session()

    try:
        auth = await itla_auth.run(email, password)

        if auth["success"]:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_user_id(user_id)

            encrypted_password = await encrypt(password)

            if user is None:
                await user_repo.create(user_id, email, encrypted_password)
                return {"auth": True, "type": "register"}

            else:
                await user_repo.update(
                    user_id,
                    email,
                    encrypted_password,
                )
                return {"auth": True, "type": "updated"}
        else:
            return {"auth": False, "type": "invalid"}

    except Exception as e:
        raise ValueError("Hubo un error registrando al usuario", e)

    finally:
        session.close()
