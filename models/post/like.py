from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Index
from ..base import TimestampMixin

if TYPE_CHECKING:
    from .post import Post
    from ..user.user import User

class Like(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "likes"
    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="posts.id", ondelete="CASCADE")
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")

    post: Optional["Post"] = Relationship(back_populates="likes")
    user: Optional["User"] = Relationship(back_populates="likes")

    __table_args__ = (Index('uq_user_post_like', 'user_id', 'post_id', unique=True),)
