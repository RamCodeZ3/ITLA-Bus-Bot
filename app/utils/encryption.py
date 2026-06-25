import base64
import os

from dotenv import load_dotenv
from cryptography.fernet import Fernet


def _load_key() -> bytes:
    load_dotenv()
    KEY = os.getenv("ENCRYPTION_KEY")

    if not KEY:
        raise RuntimeError("ENCRYPTION_KEY is not valid Fernet key")

    try:
        base64.urlsafe_b64decode(KEY)

    except Exception as e:
        raise RuntimeError("ENCRYPTION_KEY is not valid Fernet key", e)

    return KEY.encode()


_fernet = Fernet(_load_key())


async def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


async def descrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()
