from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, HttpUrl, computed_field
from sqlmodel import Field


class PostBase(BaseModel):
    title: str
    message: str
    category: str
    post_type_id: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_text: Optional[str] = None


class PostMultimediaInput(BaseModel):
    url: HttpUrl


class PostMultimediaRead(BaseModel):
    id: int
    url: HttpUrl
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PostCreate(PostBase):
    model_config = {
        "json_schema_extra": {"from_attributes": True}
    }


class PostPatch(BaseModel):
    title: str | None = None
    message: str | None = None
    category: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    location_text: str | None = None
    multimedia: list[PostMultimediaInput] | None = None


class LikeRead(BaseModel):
    user_id: int
    post_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PostRead(PostBase):
    id: int
    username: str | None = None
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None
    multimedia: list[PostMultimediaRead]
    likes: list[LikeRead] = Field(default=[], exclude=True)

    # Expuesto explícitamente para los clientes que aún leen city_name
    city_name: str = "Sin ubicación"

    @computed_field
    def likes_count(self) -> int:
        return len(self.likes)

    model_config = {"from_attributes": True}


class PostFilters(BaseModel):
    user_id: int | None = None
    category: str | None = None
    post_type_id: int | None = None
    keyword: str | None = None
    skip: int = 0
    limit: int = 10
    most_liked: bool = False  # kept for backward compat — prefer sort_by
    sort_by: Literal['newest', 'most_liked', 'closest'] = 'newest'
    show_only_active: bool | None = None
    # Filtro geográfico por radio
    lat: float | None = None
    lon: float | None = None
    radius_km: float = 20.0
