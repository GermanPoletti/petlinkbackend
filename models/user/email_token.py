from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class EmailVerificationToken(SQLModel, table=True):
    __tablename__: str = "email_verification_tokens"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    token: str = Field(max_length=64, unique=True, index=True)
    expires_at: datetime
    used: bool = Field(default=False)
