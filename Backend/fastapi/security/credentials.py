from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from Backend.config import Telegram
from typing import Optional
import hashlib

ADMIN_PASSWORD_HASH = hashlib.sha256(Telegram.ADMIN_PASSWORD.encode()).hexdigest()

security = HTTPBearer(auto_error=False)

def verify_password(password: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH

def verify_credentials(username: str, password: str) -> bool:
    return username == Telegram.ADMIN_USERNAME and verify_password(password)

def is_authenticated(request: Request) -> bool:
    return request.session.get("authenticated", False)

def require_auth(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Authentication required")
    return True

def get_current_user(request: Request) -> Optional[str]:
    if is_authenticated(request):
        return request.session.get("username")
    return None
