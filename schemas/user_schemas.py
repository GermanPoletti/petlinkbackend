from pydantic import BaseModel, EmailStr
import datetime

class UserBase(BaseModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    photo_url: str | None = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    role_id: int
    status_id: int   
    id: int
    created_at: datetime.datetime
    
class UserPatch(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    photo_url: str | None = None
    password: str | None = None

