from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field


class UserPushToken(SQLModel, table=True):
    __tablename__ = "user_push_tokens"

    user_id: int = Field(primary_key=True, foreign_key="users.id", ondelete="CASCADE")
    token: str = Field(max_length=500)
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
