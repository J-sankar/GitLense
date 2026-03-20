from pydantic import BaseModel, EmailStr, ConfigDict
from uuid import UUID

class RegisterRequest(BaseModel):
    username :str
    email: EmailStr
    password: str



class LoginRequest( BaseModel) :
    email : str
    password: str


class RegisterResponse( BaseModel):
    id: UUID
    username: str
    email: str

    class Config:
        from_attributes = True



class UserResponse(BaseModel):
    id:       UUID
    username: str
    email:    str

    class Config:
        from_attributes = True



class TokenResponse(BaseModel):
    access_token : str
    token_type :str = "bearer"
    user: UserResponse



class RefreshRequest(BaseModel):
    refresh_token: str