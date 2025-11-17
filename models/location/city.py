from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from ..base import TimestampMixin

if TYPE_CHECKING:
    from .state_province import StateProvince
    from ..post.post import Post

class City(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "cities"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    state_province_id: int = Field(foreign_key="state_provinces.id", ondelete="RESTRICT")

    state_province: Optional["StateProvince"] = Relationship(back_populates="cities")
    posts: List["Post"] = Relationship(back_populates="city")
