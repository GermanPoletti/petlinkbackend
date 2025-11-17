from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from ..base import TimestampMixin

if TYPE_CHECKING:
    from .country import Country
    from .city import City

class StateProvince(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "state_provinces"
    id: int | None = Field(default=None, primary_key=True)
    country_id: int = Field(foreign_key="countries.id", ondelete="RESTRICT")
    name: str = Field(max_length=100)

    country: Optional["Country"] = Relationship(back_populates="state_provinces")
    cities: List["City"] = Relationship(back_populates="state_province")
