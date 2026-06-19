from datetime import timedelta, timezone, datetime
import jwt
from jwt.exceptions import PyJWTError as JWTError
from fastapi import Header, Response, Request, Query

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from src.core.database import get_db

from src.core.config import settings
from src.core.logger import get_logger
import hashlib

# from src.models.db import RefreshToken

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import uuid
import bcrypt


logger = get_logger(__name__)



def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    # Decode back to a standard string to save cleanly to PostgreSQL
    return hashed_bytes.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode('utf-8'),
            hashed.encode('utf-8')
        )
    except Exception:
        return False


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4()),
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}

    return jwt.encode(payload, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}")
        return None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


COOKIE_NAME = "refresh_token"




def set_refresh_cookies(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,  # Prevents JS access
        secure=settings.ENVIRONMENT
        == "production",  # Only sends over HTTPS (disable for local dev if not using SSL)
        samesite="lax",  # CSRF protection
        max_age=7 * 24 * 60 * 60,  # 7 days matches your JWT exp
    )


def get_refresh_cookies(request: Request) -> str | None:
    return request.cookies.get(COOKIE_NAME)


def clear_refresh_cookie(response: Response):
    response.delete_cookie(key=COOKIE_NAME, httponly=True, secure=True, samesite="lax")


bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    from src.models.db import User

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        logger.error("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        logger.error(f"User not found : {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


def get_current_user_from_query(
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db),
):
    from src.models.db import User

    logger.debug(f"SSE token received: {token[:20]}...")

    if not token:
        logger.error("Token not provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token not provided"
        )

    payload = decode_token(token)
    if not payload:
        logger.debug("Invalid or expired token type")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    if payload.get("type") != "access":
        logger.debug("Invalid token type")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )

    user_id = payload.get("sub")
    logger.debug(f"User ID from token: {user_id}")
    user = db.query(User).filter(User.id == uuid.UUID(str(user_id))).first()

    if not user:
        logger.error(f"User not found: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    logger.info(f"SSE auth success for user: {user.username}")

    return user


async def get_gateway_user(
    # FastAPI automatically converts "X-User-ID" to a variable name, 
    # but using 'alias' ensures exact matching
    x_user_id: str | None = Header(default=None, alias="X-User-ID")
) -> uuid.UUID:
    """
    Extracts the authenticated user's ID from the NGINX gateway header.
    """
    if not x_user_id:
        # If NGINX is configured correctly, this should never happen,
        # but it protects you if someone accidentally opens the container port directly.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Missing User ID header. Are you bypassing the gateway?"
        )
    
    try:
        # Convert the string header back into a Python UUID object for your database
        return uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid User ID format"
        )