from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("SECRET_KEY").encode()
cipher = Fernet(key)

def encrypt_session(session_string: str) -> str:
    return cipher.encrypt(session_string.encode()).decode()

def decrypt_session(encrypted_session: str) -> str:
    return cipher.decrypt(encrypted_session.encode()).decode()
