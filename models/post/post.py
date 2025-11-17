from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, TEXT, Index
from ..base import TimestampMixin
from ..enums import PostTypeEnum
from datetime import datetime

if TYPE_CHECKING:
    from ..user.user import User
    from ..location.city import City
    from ..core.post_type import PostType
    from .post_multimedia import PostMultimedia
    from .like import Like
    from .report import Report
    from ..chat.chat import Chat
    from ..agreement.agreement import Agreement

# Post Type Ids:
# class PostTypeEnum(IntEnum):
#     OFERTA = 1
#     NECESIDAD = 2


class Post(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "posts"
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    title: str = Field(max_length=255)
    message: str = Field(sa_column=Column(TEXT))
    category: str = Field(max_length=100)
    post_type_id: int = Field(foreign_key="post_types.id", ondelete="RESTRICT")
    is_active: bool = Field(default=True)
    city_id: int = Field(foreign_key="cities.id", ondelete="RESTRICT")
    deleted_at: Optional[datetime] = Field(default=None, index=True)


    user: Optional["User"] = Relationship(back_populates="posts")
    city: Optional["City"] = Relationship(back_populates="posts")
    post_type: Optional["PostType"] = Relationship(back_populates="posts")
    agreements: List["Agreement"] = Relationship(back_populates="post", cascade_delete=True)
    chats: List["Chat"] = Relationship(back_populates="post", cascade_delete=True)
    multimedia: List["PostMultimedia"] = Relationship(back_populates="post", cascade_delete=True)
    likes: List["Like"] = Relationship(back_populates="post", cascade_delete=True)
    reports: List["Report"] = Relationship(back_populates="post", cascade_delete=True)

    __table_args__ = (
        Index('idx_user_city_active', 'user_id', 'city_id', 'is_active'),
        Index('idx_category_date', 'category', 'created_at'),
        Index('idx_type_date', 'post_type_id', 'created_at'),
        Index('idx_active_city_type', 'is_active', 'city_id', 'post_type_id', 'created_at'),
    )
