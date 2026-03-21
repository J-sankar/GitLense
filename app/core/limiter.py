from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi import Request
from app.core.security import decode_token
from app.core.logger import get_logger

logger = get_logger(__name__)

def get_user_id(request: Request) ->str:
    try:
        auth  = request.headers.get("Authorization", "")
        token = auth.replace("Bearer", "")
        if token:
            payload = decode_token(token)
            if payload:
                return payload.get("sub")
    except Exception:
        pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_user_id)

