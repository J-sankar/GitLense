from datetime import timedelta, timezone, datetime
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logger import get_logger


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
