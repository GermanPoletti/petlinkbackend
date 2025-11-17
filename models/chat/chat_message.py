from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, TEXT, Index
from ..base import TimestampMixin

if TYPE_CHECKING:
    from .chat import Chat
    from ..user.user import User

class ChatMessage(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "chat_messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(foreign_key="chats.id", ondelete="CASCADE")
    sender_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    message: str = Field(sa_column=Column(TEXT))

    chat: Optional["Chat"] = Relationship(back_populates="messages")
    sender: Optional["User"] = Relationship(back_populates="sent_messages")

    __table_args__ = (Index('idx_chat_sent', 'chat_id', 'created_at'),)
