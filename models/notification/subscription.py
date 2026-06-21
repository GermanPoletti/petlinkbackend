from typing import Optional
from sqlmodel import SQLModel, Field, UniqueConstraint


class NotificationSubscription(SQLModel, table=True):
    __tablename__ = "notification_subscriptions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    post_type_id: int = Field(foreign_key="post_types.id", ondelete="CASCADE")
    category: str = Field(max_length=100)

    __table_args__ = (
        UniqueConstraint("user_id", "post_type_id", "category", name="uq_sub"),
    )
