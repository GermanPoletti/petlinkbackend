from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, TEXT, Index
from ..base import TimestampMixin

if TYPE_CHECKING:
    from .post import Post

class PostMultimedia(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "post_multimedia"
    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="posts.id", ondelete="CASCADE")
    url: str = Field(sa_column=Column(TEXT))

    post: Optional["Post"] = Relationship(back_populates="multimedia")

    __table_args__ = (Index('idx_post_uploaded', 'post_id', 'created_at'),)
