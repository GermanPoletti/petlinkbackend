from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Index
from ..base import TimestampMixin
from datetime import datetime

if TYPE_CHECKING:
    from .user import User

class TokensBlacklist(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "tokens_blacklist"
    id: int | None = Field(default=None, primary_key=True)
    jti: str = Field(max_length=36, unique=True, index=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    expires_at: datetime = Field(nullable=False)

    user: Optional["User"] = Relationship(back_populates="blacklisted_tokens")

    __table_args__ = (Index('idx_expires_jti', 'expires_at', 'jti'),)
