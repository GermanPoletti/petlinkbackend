from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from ..base import TimestampMixin

if TYPE_CHECKING:
    from .state_province import StateProvince

class Country(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "countries"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    code: str = Field(max_length=2, unique=True, index=True)

    state_provinces: List["StateProvince"] = Relationship(back_populates="country")
