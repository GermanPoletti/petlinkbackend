from pydantic import BaseModel, EmailStr, Field, field_validator
from email_validator import validate_email, EmailNotValidError
import datetime

class UserBase(BaseModel):
    email: EmailStr

    @field_validator("email")
    def validate_real_email(cls, v):
        try:
            return validate_email(v, check_deliverability=True).normalized
        except EmailNotValidError as e:
            raise ValueError(str(e))

class UserFilters(BaseModel):
    role: str | None = None
    email: str | None = None
    username: str | None = None
    model_config = {
        "from_attributes": True
    }


class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserInfoRead(BaseModel):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None

    model_config = {"from_attributes": True}

class UserRead(BaseModel):
    id: int
    email: EmailStr
    help_count: int
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
    password: str | None = Field(default=None, min_length=8)

    @field_validator("email")
    def validate_real_email(cls, v):
        try:
            return validate_email(v, check_deliverability=True).normalized
        except EmailNotValidError as e:
            raise ValueError(str(e))

