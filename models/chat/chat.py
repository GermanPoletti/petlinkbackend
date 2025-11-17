from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Index
from ..base import TimestampMixin
from datetime import datetime

if TYPE_CHECKING:
    from ..post.post import Post
    from ..user.user import User
    from .chat_message import ChatMessage

class Chat(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "chats"
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="posts.id", ondelete="CASCADE")
    initiator_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    receiver_id: int = Field(foreign_key="users.id", ondelete="CASCADE")

    post: Optional["Post"] = Relationship(back_populates="chats")
    initiator: Optional["User"] = Relationship(
        back_populates="initiated_chats",
        sa_relationship_kwargs={"foreign_keys": "Chat.initiator_id"}
    )
    receiver: Optional["User"] = Relationship(
        back_populates="received_chats",
        sa_relationship_kwargs={"foreign_keys": "Chat.receiver_id"}
    )
    messages: List["ChatMessage"] = Relationship(back_populates="chat", cascade_delete=True)

    __table_args__ = (
        Index('uq_post_initiator', 'post_id', 'initiator_id', unique=True),
        Index('idx_chats_receiver', 'receiver_id'),
        Index('idx_chats_post_receiver', 'post_id', 'receiver_id'),
    )
