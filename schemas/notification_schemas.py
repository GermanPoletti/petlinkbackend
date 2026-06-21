from pydantic import BaseModel
from typing import Optional


class TokenRegister(BaseModel):
    token: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SubscriptionItem(BaseModel):
    post_type_id: int
    category: str


class SubscriptionUpdate(BaseModel):
    subscriptions: list[SubscriptionItem]


class SubscriptionRead(BaseModel):
    post_type_id: int
    category: str

    model_config = {"from_attributes": True}
