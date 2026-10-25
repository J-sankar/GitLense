from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi import Request
from src.core.security import decode_token
from src.core.logger import get_logger

logger = get_logger(__name__)

def get_user_id(request: Request) ->str:
    try:
        auth  = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ")[1]
        else:
            token = auth.strip()
        if token:
            payload = decode_token(token)
            if payload:
                return payload.get("sub")
    except Exception:
        pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_id)

