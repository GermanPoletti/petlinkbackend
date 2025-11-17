from typing import List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from ..base import TimestampMixin

if TYPE_CHECKING:
    from ..post.post import Post

class PostType(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "post_types"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=50, unique=True)

    posts: List["Post"] = Relationship(back_populates="post_type")
