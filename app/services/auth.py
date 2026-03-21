from sqlalchemy.orm import Session
from sqlalchemy import asc
from fastapi import HTTPException, status
from app.core.logger import get_logger
from app.models.db import User
from app.core.security import (hash_password,verify_password,create_access_token,create_refresh_token,save_refresh_token)



logger = get_logger(__name__)



def register_user(
        db: Session ,
        username : str,
        email: str,
        password : str
) -> User :
    try:
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user :
            logger.info(f"email already exists : {email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail= "email already exists"
            )
        
        if db.query(User).filter(User.username == username).first():
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
        db.commit()
        db.refresh(user)
        return user
    except HTTPException:
        raise 
    except Exception as e :
        db.rollback()
        logger.error(f"Failed to register user : {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    


def login_user(
        db: Session ,
        email: str,
        password : str
) -> dict :
    try :
        user = db.query(User).filter(User.email == email).first()

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
        logger.info(f"Access token created") 
        refresh_token = create_refresh_token(user_id=str(user.id))
        logger.info(f"Refresh token created")       
        save_refresh_token(db,user_id=str(user.id), token=refresh_token)
        logger.info(f"Refresh token saved")

        logger.info(f"User verified , email : {email}")
        return {
            "user": user,
            "access_token":access_token,
            "refresh_token" : refresh_token
        }
    except HTTPException:

        raise
    except Exception as e :
        db.rollback()
        logger.error(f"Failed to verify: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


    