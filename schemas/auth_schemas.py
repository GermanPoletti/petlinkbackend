from pydantic import BaseModel, EmailStr


class LoginData(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    user_id: int
    access_token: str
    token_type: str = "bearer"
    expires_at: int
    

class TokenData(BaseModel):
    pass