from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.database import SessionDep

from dependencies.auth_dependencies import get_current_user
from models import Post
from models.user.user import User
from schemas import PostCreate, PostPatch, PostFilters
from schemas.post_schemas import PostRead
from services import post_service
from exceptions.exceptions import NotOwnerError, PostNotFoundException
from services.mapper import map_ids_to_names, MapperError


router = APIRouter(prefix="/posts", tags=["posts"])

#TODO: hacer que las request y responses pidan y devuelvan nombres en vez de ids mediante funciones genericas
#TODO: Search posts by keywords


@router.post("/", description="Creates a post", response_model=PostRead)
def create_post(
    session: SessionDep,
    post_data: PostCreate,
    current_user: User = Depends(get_current_user)
):
    assert current_user.id is not None
    return post_service.create_post(session, post_data, current_user.id)

@router.get("/", description="Retrieves a paginated list of posts, with optional skip and limit parameters.")
def get_posts(session: SessionDep, filters: Annotated[PostFilters, Query()], current_user: User =Depends(get_current_user)):
    posts = post_service.get_posts(session=session, filters=filters)
    
    return {"posts": posts if posts else "No hay posts",
            "limit_reached": True if len(posts) < filters.limit else False}

@router.get("/search")
def search_post(keyword: str, session: SessionDep, current_user: User = Depends(get_current_user)):
    return post_service.search_post(session=session, keyword= keyword)

@router.get("/{post_id}", description="Retrieves a post by its ID.")
def get_post_by_id(session: SessionDep, post_id: int, current_user: User = Depends(get_current_user)):
    try:
        post = post_service.get_post_by_id(session, post_id)
        data = post.model_dump()
        data["likes"] = post.likes_count
        return data
    except(PostNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado")

@router.patch("/{post_id}", description="Updates a post; only allowed if the current user is the owner.")
def edit_post(session: SessionDep, post_id: int, post_data: PostPatch, current_user: User = Depends(get_current_user)):
    try:
        return post_service.patch_post(session, post_id, post_data, current_user.id)
    except NotOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except PostNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

#TODO: Admin can delete even though its not owner
@router.delete("/{post_id}", description="Deletes a post; allowed for the owner or an admin user.")
def delete_post(session: SessionDep, post_id: int, current_user: User = Depends(get_current_user)):
    try:
        return post_service.delete_post(session, post_id, current_user)
    except NotOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except PostNotFoundException as e:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.post("/{post_id}/like", description="Likes or unlikes the post depending on whether it’s already liked.")
def like_post(session: SessionDep, post_id: int, current_user: User = Depends(get_current_user)):
    try:    
        assert current_user.id is not None
        return post_service.like_post(session=session, post_id=post_id, user_id=current_user.id)
    except PostNotFoundException as e:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
