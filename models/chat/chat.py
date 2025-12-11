from typing import Optional, List, TYPE_CHECKING
from sqlmodel import TEXT, Column, SQLModel, Field, Relationship, Index
from ..base import TimestampMixin
from datetime import datetime

if TYPE_CHECKING:
    from ..post.post import Post
    from ..user.user import User
    from .chat_message import ChatMessage

class Chat(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "chats"

    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="posts.id", ondelete="CASCADE")
    initiator_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    receiver_id: int = Field(foreign_key="users.id", ondelete="CASCADE")

    status_id: int = Field(default=1, foreign_key="status_agreements.id")
    closing_date: datetime | None = Field(default=None)
    resolution_note: str | None = Field(default=None, sa_column=Column(TEXT))
    is_active: bool = Field(default=True)

    # Relaciones
    post: Optional["Post"] = Relationship(back_populates="chats")
    initiator: Optional["User"] = Relationship(
        back_populates="initiated_chats",
        sa_relationship_kwargs={
            "foreign_keys": "Chat.initiator_id",   # ← CLAVE
            "lazy": "joined"
        }
    )

    receiver: Optional["User"] = Relationship(
        back_populates="received_chats",
        sa_relationship_kwargs={
            "foreign_keys": "Chat.receiver_id",    # ← CLAVE
            "lazy": "joined"
        }
    )
    messages: List["ChatMessage"] = Relationship(back_populates="chat")

    # Solo este si querés estar paranoico con la unicidad
    __table_args__ = (
        Index("uq_post_initiator", "post_id", "initiator_id", unique=True),
    )
