from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Index
from ..base import TimestampMixin
from ..enums import AgreementStatusEnum
from datetime import datetime

if TYPE_CHECKING:
    from ..post.post import Post
    from ..user.user import User
    from ..core.status_agreement import StatusAgreement

class Agreement(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "agreements"
    id: Optional[int] = Field(default=None, primary_key=True)
    post_id: int = Field(foreign_key="posts.id", ondelete="CASCADE")
    initiator_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    receiver_id: int = Field(foreign_key="users.id", ondelete="CASCADE")
    closing_date: Optional[datetime] = Field(default=None)
    status_id: int = Field(foreign_key="status_agreements.id", ondelete="RESTRICT")

    post: Optional["Post"] = Relationship(back_populates="agreements")
    initiator: Optional["User"] = Relationship(
        back_populates="initiated_agreements",
        sa_relationship_kwargs={"foreign_keys": "Agreement.initiator_id"}
    )
    receiver: Optional["User"] = Relationship(
        back_populates="received_agreements",
        sa_relationship_kwargs={"foreign_keys": "Agreement.receiver_id"}
    )
    status: Optional["StatusAgreement"] = Relationship(back_populates="agreements")

    __table_args__ = (
        Index('idx_status_dates', 'status_id', 'created_at'),
        Index('idx_users_status', 'initiator_id', 'receiver_id', 'status_id'),
    )
