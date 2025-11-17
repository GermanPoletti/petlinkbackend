from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Index
from datetime import datetime

from models.base import TimestampMixin

if TYPE_CHECKING:
    from .user import User


class ActiveToken(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "active_tokens"
    
    user_id: int = Field(
        primary_key=True,
        foreign_key="users.id",
        ondelete="CASCADE",
        description="PK → solo 1 token activo por usuario, punto final."
    )
    
    jti: str = Field(
        max_length=36,
        unique=True,
        index=True,
        description="JWT ID (jti) - identificador único del token activo"
    )
    
    expires_at: datetime = Field(
        index=True,
        nullable=False,
        description="Fecha de expiración del token"
    )


    user: Optional["User"] = Relationship(back_populates="active_token")

