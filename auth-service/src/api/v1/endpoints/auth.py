from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends, APIRouter, Response, Request, HTTPException, status
from src.core.limiter import limiter
from src.core.logger import get_logger
from src.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RegisterRequest,
    UserResponse,
    RegisterResponse,
)
from src.models.db import User
from src.core.database import get_db
from src.services.auth import register_user, login_user
from src.core.security import (
    get_current_user,
    decode_token,
    create_access_token,
    create_refresh_token,
    set_refresh_cookies,
    get_refresh_cookies,
    verify_refresh_token,
    delete_refresh_token,
    save_refresh_token,
    clear_refresh_cookie,
    bearer_scheme
)
from fastapi.security import HTTPAuthorizationCredentials
from src.core.config import settings
import uuid

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    path="/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute")
async def register(
    request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)
):
    user = await register_user(
        db=db, username=payload.username, email=payload.email, password=payload.password
    )
    if user:
        logger.info(f"User registered successfully, id: {user.id}")

    return user


@router.post(path="/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    data = await login_user(db, email=payload.email, password=payload.password)

    user_obj = data.get("user")
    at = data.get("access_token")  # Correct access
    rt = data.get("refresh_token")

    set_refresh_cookies(response, rt)

    return TokenResponse(
        access_token=at,
        token_type="access",
        user=user_obj,  # Pydantic handles the conversion automatically
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("5/minute")
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    refresh_token = get_refresh_cookies(request)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found"
        )
    stored = await verify_refresh_token(db, refresh_token)
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    token_payload = decode_token(refresh_token)
    if not token_payload or token_payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )
    result = await db.execute(
        select(User).where(User.id == uuid.UUID(token_payload["sub"]))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    await delete_refresh_token(db, refresh_token)
    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))
    await save_refresh_token(db, str(user.id), new_refresh_token)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,  # Prevents JS access
        secure=settings.ENVIRONMENT
        == "production",  # Only sends over HTTPS (disable for local dev if not using SSL)
        samesite="lax",  # CSRF protection
        max_age=7 * 24 * 60 * 60,  # 7 days matches your JWT exp
    )

    return TokenResponse(
        access_token=new_access_token,
        user=UserResponse(id=user.id, username=user.username, email=user.email),
    )


@router.post("/logout")
@limiter.limit("5/minute")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # ── get refresh token from cookie ─────────────────
    refresh_token = get_refresh_cookies(request)

    if refresh_token:
        await delete_refresh_token(db, refresh_token)
        logger.info(f"Refresh token deleted for user {str(current_user.id)[:8]}")
    else:
        logger.warning(
            f"No refresh token found in cookie for user {str(current_user.id)[:8]}"
        )

    # ── clear cookie ──────────────────────────────────
    clear_refresh_cookie(response)

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return await current_user


@router.get("/validate")
async def validate_token_for_nginx(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    
    token = credentials.credentials
    
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid or expired token"
        )
        
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="User ID missing from payload"
        )
        
    
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"X-User-ID": str(user_id)}
    )