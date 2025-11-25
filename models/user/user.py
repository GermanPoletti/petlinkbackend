from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, TEXT, Index
from ..base import TimestampMixin
from ..enums import RoleEnum, StatusUserEnum
from pydantic import field_validator
from datetime import datetime

if TYPE_CHECKING:
    from ..core.role import Role
    from ..core.status_user import StatusUser
    from ..post.post import Post
    from ..chat.chat import Chat, ChatMessage
    from ..agreement.agreement import Agreement
    from ..post.like import Like
    from ..post.report import Report
    from .active_tokens import ActiveToken
    from .tokens_blacklist import TokensBlacklist
    from .active_tokens import ActiveToken

class User(SQLModel, TimestampMixin, table=True):
    __tablename__: str = "users"
    id: int | None = Field(default=None, primary_key=True)
    password_hash: str = Field(max_length=255)
    email: str = Field(max_length=255, unique=True, index=True)
    
    role_id: int = Field(default=RoleEnum.USER ,foreign_key="roles.id", ondelete="RESTRICT")
    status_id: int = Field(default=StatusUserEnum.ACTIVE ,foreign_key="status_users.id", ondelete="RESTRICT")
    deleted_at: datetime | None = Field(default=None, index=True)

    role: Optional["Role"] = Relationship(back_populates="users")
    status: Optional["StatusUser"] = Relationship(back_populates="users")
    posts: List["Post"] = Relationship(back_populates="user", cascade_delete=True)
    user_info: Optional["UserProfiles"] = Relationship(back_populates="user")


    initiated_agreements: List["Agreement"] = Relationship(
        back_populates="initiator",
        sa_relationship_kwargs={"foreign_keys": "[Agreement.initiator_id]"}
    )
    received_agreements: List["Agreement"] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": "[Agreement.receiver_id]"}
    )
    initiated_chats: List["Chat"] = Relationship(
        back_populates="initiator",
        sa_relationship_kwargs={"foreign_keys": "[Chat.initiator_id]"}
    )
    received_chats: List["Chat"] = Relationship(
        back_populates="receiver",
        sa_relationship_kwargs={"foreign_keys": "[Chat.receiver_id]"}
    )
    
    sent_messages: List["ChatMessage"] = Relationship(back_populates="sender")
    likes: List["Like"] = Relationship(back_populates="user")
    reports: List["Report"] = Relationship(back_populates="reporting_user")
    blacklisted_tokens: List["TokensBlacklist"] = Relationship(back_populates="user")
    active_token: Optional["ActiveToken"] = Relationship(back_populates="user")


    @field_validator("role_id")
    @classmethod
    def validate_role(cls, value):
        return RoleEnum(value)

    @field_validator("status_id")
    @classmethod
    def validate_status(cls, value):
        return StatusUserEnum(value)

class UserProfiles(SQLModel, table = True):
    __tablename__: str = "user_profiles"

    user_id: int = Field(primary_key=True, foreign_key="users.id")
    username: str | None = Field(default=None, max_length=50, unique=True, index=True)
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)
    photo_url: str | None = Field(default=None, sa_column=Column(TEXT))
    
    user: Optional["User"] = Relationship(back_populates="user_info")

