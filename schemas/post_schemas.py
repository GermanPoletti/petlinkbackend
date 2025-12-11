from datetime import datetime
from pydantic import BaseModel, HttpUrl, computed_field
from sqlmodel import Field

class PostBase(BaseModel):
    title: str
    message: str
    category: str
    post_type_id: int
    city_name: str
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
    city_id: int | None = None
    multimedia: list[PostMultimediaInput] | None = None

class LikeRead(BaseModel):
    user_id: int
    post_id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

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

    
    city_name: str = "Ubicación desconocida"  # ← inyectamos manual

    @computed_field
    def likes_count(self) -> int:
        return len(self.likes)

    model_config = {
        "from_attributes": True
    }

# schemas/post.py
class PostFilters(BaseModel):
    user_id: int | None = None
    category: str | None = None
    city_id: int | None = None
    city: str | None = None
    province_id: int | None = None
    post_type_id: int | None = None        # ← NUEVO
    keyword: str | None = None             # ← NUEVO
    skip: int = 0
    limit: int = 10
    most_liked: bool = False
    show_only_active: bool | None = None