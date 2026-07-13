import base64
import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

def _get_fernet_instance():
    key = os.getenv("ENCRYPTION_KEY")
    
    if not key:
        return None

    try:
        base64.urlsafe_b64decode(key)
        return Fernet(key.encode())
    except Exception:
        return None


async def encrypt(value: str) -> str:
    fernet = _get_fernet_instance()
    
    if not fernet:
        return value
        
    return fernet.encrypt(value.encode()).decode()


async def descrypt(value: str) -> str:
    fernet = _get_fernet_instance()
    
    if not fernet:
        return value
        
    try:
        return fernet.decrypt(value.encode()).decode()
    except Exception:
        return value
