from pydantic import BaseModel, EmailStr
import datetime

class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str

class UserInfoRead(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None

    model_config = {"from_attributes": True}

class UserRead(BaseModel):
    id: int
    email: EmailStr
    
    role_id: int
    status_id: int
    
    created_at: datetime.datetime
    updated_at: datetime.datetime | None = None
    deleted_at: datetime.datetime | None = None

    user_info: UserInfoRead | None = None

    model_config = {"from_attributes": True}
    
class UserPatch(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    photo_url: str | None = None
    password: str | None = None

