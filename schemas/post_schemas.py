from datetime import datetime
from pydantic import BaseModel, HttpUrl, computed_field
from sqlmodel import Field

class PostBase(BaseModel):
    title: str
    message: str
    category: str
    post_type_id: int
    city_id: int

class PostMultimediaInput(BaseModel):
    url: HttpUrl

class PostCreate(PostBase):
    multimedia: list[PostMultimediaInput] = []

    model_config = {
        "json_schema_extra": {
            "from_attributes": True,
            # "examples": [
            #     """{
            #         "title": "My Post Title",
            #         "message": "This is the content of the post.",
            #         "category": "General",
            #         "post_type_id": 1,
            #         "city_id": 2,
            #         "multimedia": [
            #             {"url": "http://example.com/image1.jpg"},
            #             {"url": "http://example.com/image2.jpg"}
            #         ]
            #     }"""
            # ]
        }
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
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None
    likes: list[LikeRead] = Field(default=[], exclude=True)

    @computed_field
    def likes_count(self) -> int:
        return len(self.likes)

    model_config = {
        "from_attributes": True
    }

class PostFilters(BaseModel):
    category: str | None = None
    city_id: int | None = None
    province_id: int | None = None
    skip: int = 0
    limit: int= 10
    most_liked: bool = False
    show_only_active: bool | None = None