from typing import List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from ..user.user import User

class Role(SQLModel, table=True):
    __tablename__: str = "roles"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=50, unique=True)

    users: List["User"] = Relationship(back_populates="role")
