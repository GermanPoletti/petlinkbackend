from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Index
from ..base import TimestampMixin

if TYPE_CHECKING:
    from .post import Post
    from ..user.user import User

class Report(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "reports"
    id: int | None = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="posts.id", ondelete="CASCADE")
    reporting_user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    reason: str = Field(max_length=255)
    is_reviewed: bool = Field(default=False)

    post: Optional["Post"] = Relationship(back_populates="reports")
    reporting_user: Optional["User"] = Relationship(back_populates="reports")

    __table_args__ = (
        Index('idx_reports_post', 'post_id'),
        Index('idx_reports_user', 'reporting_user_id'),
    )
