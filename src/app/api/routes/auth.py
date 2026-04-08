from sqlalchemy.orm import Session
from fastapi import  Depends,APIRouter, Response,Request, HTTPException,status
from app.core.limiter import limiter
from app.core.logger import get_logger
from app.schemas.auth import (LoginRequest, TokenResponse, RegisterRequest, UserResponse,RegisterResponse)
from app.models.db import User
from app.core.database import get_db
from app.services.auth import register_user, login_user
from app.core.security import get_current_user,decode_token,create_access_token,create_refresh_token,set_refresh_cookies,get_refresh_cookies,verify_refresh_token,delete_refresh_token, save_refresh_token,clear_refresh_cookie
from app.core.config import settings
import uuid

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post(path="/register",response_model=RegisterResponse,status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
def register(
    request:Request,
    payload : RegisterRequest,  db: Session = Depends(get_db)
):
    user = register_user(db=db,username=payload.username, email=payload.email, password=payload.password)
    if user :
        logger.info(f"User registered successfully, id: {user.id}")
    
    return user

@router.post(path="/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request:Request,
    payload: LoginRequest,response:Response, db : Session = Depends(get_db)
) :
    data = login_user(db,email=payload.email, password=payload.password)

    user_obj = data.get("user")
    at = data.get("access_token") # Correct access
    rt = data.get("refresh_token")

    set_refresh_cookies(response,rt)
    
    return TokenResponse(
        access_token=at,
        token_type="access",
        user=user_obj # Pydantic handles the conversion automatically
    )



@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("5/minute")
def refresh(
    request:  Request,
    response: Response,
    db:       Session = Depends(get_db)
):
    refresh_token = get_refresh_cookies(request)
    if not refresh_token:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Refresh token not found"
        )
    stored = verify_refresh_token(db, refresh_token)
    if not stored:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid or expired refresh token"
        )
    token_payload = decode_token(refresh_token)
    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid token type"
        )
    
    user = db.query(User).filter(
        User.id == uuid.UUID(token_payload["sub"])
    ).first()

    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "User not found"
        )
    
    delete_refresh_token(db, refresh_token)
    new_access_token  = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))
    save_refresh_token(db, str(user.id), new_refresh_token)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,   # Prevents JS access
        secure=settings.ENVIRONMENT == "production",     # Only sends over HTTPS (disable for local dev if not using SSL)
        samesite="lax",  # CSRF protection
        max_age=7 * 24 * 60 * 60, # 7 days matches your JWT exp
    )

    return TokenResponse(
        access_token = new_access_token,
        user         = UserResponse(
            id       = user.id,
            username = user.username,
            email    = user.email
        )
    )

@router.post("/logout")
@limiter.limit("5/minute")
def logout(
    request:      Request,
    response:     Response,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db)
):
    # ── get refresh token from cookie ─────────────────
    refresh_token = get_refresh_cookies(request)

    if refresh_token:
        delete_refresh_token(db, refresh_token)
        logger.info(f"Refresh token deleted for user {str(current_user.id)[:8]}")
    else:
        logger.warning(f"No refresh token found in cookie for user {str(current_user.id)[:8]}")

    # ── clear cookie ──────────────────────────────────
    clear_refresh_cookie(response)

    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user