from datetime import timedelta, timezone, datetime
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Response,Request, Query

from sqlalchemy.orm import Session
from app.core.database import get_db

from app.core.config import settings
from app.core.logger import get_logger
import hashlib

from app.models.db import User, RefreshToken



logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"],deprecated="auto")


def hash_password(password: str) -> str :
    return pwd_context.hash(password)

def verify_password(plain:str, hashed:str) ->bool :
    return pwd_context.verify(plain,hashed)


def create_access_token(user_id: str) ->str :
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "access"
    }

    return jwt.encode(payload,settings.JWT_SECRET_KEY,settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str) ->str :
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh"
    }

    return jwt.encode(payload,settings.JWT_SECRET_KEY,settings.JWT_ALGORITHM)


def decode_token(token :str) -> str :
    try :
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decode failed: {e}")
        return None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


COOKIE_NAME="refresh_token"
def save_refresh_token(db: Session, user_id: str, token: str):
    existing_tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == uuid.UUID(user_id)
    ).order_by(RefreshToken.created_at.asc()).all()

    if len(existing_tokens) >= 2:
        db.delete(existing_tokens[0])

    db.add(RefreshToken(
        user_id    = uuid.UUID(user_id),
        token      = hash_token(token),   # ✅ store hash
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    ))
    db.commit()


def verify_refresh_token(db:Session, token: str) -> RefreshToken | None  :
    from app.core.security import decode_token
    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    token_hash = hash_token(token)
    
    return db.query(RefreshToken).filter(
        RefreshToken.user_id    == uuid.UUID(user_id),
        RefreshToken.token      == token_hash,          # ✅ compare hashes
        RefreshToken.expires_at >  datetime.now(timezone.utc)
    ).first()


def delete_refresh_token(db: Session, token: str):
    from app.core.security import decode_token
    payload = decode_token(token)
    if not payload:
        return

    user_id    = payload.get("sub")
    token_hash = hash_token(token)

    db.query(RefreshToken).filter(
        RefreshToken.user_id == uuid.UUID(user_id),
        RefreshToken.token   == token_hash
    ).delete()
    db.commit()

def set_refresh_cookies(response:Response, token:str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,   # Prevents JS access
        secure=settings.ENVIRONMENT == "production",     # Only sends over HTTPS (disable for local dev if not using SSL)
        samesite="lax",  # CSRF protection
        max_age=7 * 24 * 60 * 60, # 7 days matches your JWT exp
    )

def get_refresh_cookies(request: Request) ->str | None :
    return request.cookies.get(COOKIE_NAME)
    
def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key      = COOKIE_NAME,
        httponly = True,
        secure   = True,
        samesite = "lax"
    )

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
import uuid

bearer_scheme = HTTPBearer()

def get_current_user(
        credentials:HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: Session = Depends(get_db)

):
    from app.models.db import User

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        logger.error("Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Invalid or expired token"
        )
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid or expired token"
        )
    
    user_id = payload.get("sub")

    if not user_id :
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid token"
        )


    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()

    if not user :
        logger.error(f"User not found : {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "User not found"
        )
    
    return user


def get_current_user_from_query(
    token: str     = Query(..., description="JWT access token"),
    db:    Session = Depends(get_db)
):
    from app.models.db import User
    logger.debug(f"SSE token received: {token[:20]}...")

    if not token:
        logger.error("Token not provided")
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Token not provided"
        )
    
    payload = decode_token(token)
    if not payload:
        logger.debug("Invalid or expired token type")
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid or expired token"
        )

    if payload.get("type") != "access":
        logger.debug("Invalid token type")
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid token type"
        )

    user_id = payload.get("sub")
    logger.debug(f"User ID from token: {user_id}")
    user    = db.query(User).filter(
        User.id == uuid.UUID(str(user_id))
    ).first()

    if not user:
        logger.error(f"User not found: {user_id}") 
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "User not found"
        )
    logger.info(f"SSE auth success for user: {user.username}")

    return user
