from typing import List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from ..agreement.agreement import Agreement

class StatusAgreement(SQLModel, table=True):
    __tablename__: str = "status_agreements"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=50, unique=True)

    agreements: List["Agreement"] = Relationship(back_populates="status")
