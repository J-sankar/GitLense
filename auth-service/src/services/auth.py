from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from src.core.logger import get_logger
from src.models.db import User
from src.core.security import (hash_password,verify_password,create_access_token,create_refresh_token,save_refresh_token)



logger = get_logger(__name__)



async def register_user(
        db: AsyncSession ,
        username : str,
        email: str,
        password : str
) -> User :
    try:
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user :
            logger.info(f"email already exists : {email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail= "email already exists"
            )
        
        result = await db.execute(select(User).where(User.username == username))
        existing_username = result.scalar_one_or_none()
        if existing_username:
            logger.info(f"Username already taken {username}")
            raise HTTPException(
                status_code = status.HTTP_409_CONFLICT,
                detail      = "Username already taken"
            )
    

        user = User(
            username      = username,
            email         = email,
            password_hash = hash_password(password)
        )
        db.add(user)
        await db.commit()
        await db.flush()
        await db.refresh(user)
        return user
    except HTTPException:
        raise 
    except Exception as e :
    
        logger.error(f"Failed to register user : {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


async def login_user(
        db: AsyncSession ,
        email: str,
        password : str
) -> dict :
    try :
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            logger.debug(f"user not found , email: {email}")
            raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid email or password"
        )
        if  not verify_password(password, hashed=user.password_hash) :
            logger.debug(f"Password is incorrect , email : {email}")
            raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Invalid email or password"
        )
        


        access_token = create_access_token(user_id=str(user.id))
        logger.info("Access token created") 
        refresh_token = create_refresh_token(user_id=str(user.id))
        logger.info("Refresh token created")       
        await save_refresh_token(db,user_id=str(user.id), token=refresh_token)
        logger.info("Refresh token saved")

        logger.info(f"User verified , email : {email}")
        return {
            "user": user,
            "access_token":access_token,
            "refresh_token" : refresh_token
        }
    except HTTPException as error:

        logger.error(f"ERROR:{str(error).lower()}")
        raise
    except Exception as e :
        logger.error(f"Failed to verify: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


    