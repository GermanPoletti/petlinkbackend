from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
import json

from core.database import SessionDep
from dependencies.auth_dependencies import get_current_user
from dependencies.permissions_dependencies import require_role
from models import Post, User, RoleEnum

from schemas import PostCreate, PostPatch, PostFilters, PostRead

from services import post_service

from utils.catbox_service import upload_to_catbox
from utils.mapper import map_ids_to_names, MapperError
from utils.generics import count_rows
from exceptions.exceptions import NotOwnerError, PostNotFoundException


router = APIRouter(prefix="/posts", tags=["posts"])


MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024  # bytes


async def validate_file(file: UploadFile | None):
    if file is None:
        return None  # Post sin archivo

    # Validar extensión permitida
    allowed_ext = {"jpg", "jpeg", "png", "mp4"}
    ext = file.filename.split(".")[-1].lower() # type: ignore

    if ext not in allowed_ext:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido. Solo: {', '.join(allowed_ext)}"
        )

    # Validar tamaño
    file.file.seek(0, 2)  # ir al final
    size = file.file.tell()
    file.file.seek(0)  # volver al inicio

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"El archivo excede los {MAX_FILE_SIZE_MB} MB"
        )

    return file


@router.get("/count")
def get_posts_count(session: SessionDep, current_user: User = require_role(RoleEnum.ADMIN)):
    filters = {
        "is_active": 1
    }
    return count_rows(session=session, model= Post, filter_conditions=filters)

@router.post("/")
async def create_post(
    session: SessionDep,
    post_data: str = Form(...),  # recibe el JSON como string
    file: UploadFile | None = File(None),
    user: User = Depends(get_current_user),
):
    # Convierte el string JSON a Pydantic model
    payload = PostCreate.model_validate(json.loads(post_data))

    validated_file = await validate_file(file)
    file_url = None
    if validated_file:
        file_url = await upload_to_catbox(validated_file)  # tu función de Catbox

    post = post_service.create_post(session, payload, user.id, file_url) # type: ignore
    return post




@router.get("/", description="Retrieves a paginated list of posts, with optional skip and limit parameters.")
def get_posts(session: SessionDep, filters: Annotated[PostFilters, Query()], current_user: User =Depends(get_current_user)):
    posts = post_service.get_posts(session=session, filters=filters, user = current_user)
    
    return {"posts": posts,
            "limit_reached": True if len(posts) < filters.limit else False}

@router.get("/search", response_model=list[PostRead])
def search_post(keyword: str, session: SessionDep, current_user: User = Depends(get_current_user)):
    return post_service.search_post(session=session, keyword= keyword)

@router.get("/user/{user_id}", description="Retrives a list of post by his owner", response_model=list[PostRead])
def get_post_by_user(session: SessionDep, user_id: int, current_user: User = Depends(get_current_user)):

    return post_service.get_posts_by_user(session=session, user_id=user_id)


@router.get("/{post_id}", description="Retrieves a post by its ID.", response_model=PostRead)
def get_post_by_id(session: SessionDep, post_id: int, current_user: User = Depends(get_current_user)):
    try:
        post = post_service.get_post_by_id(session, post_id)
        data = post.model_dump()
        data["likes_count"] = post.likes_count
        return data
    except(PostNotFoundException):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post no encontrado")

@router.patch("/{post_id}", description="Updates a post; only allowed if the current user is the owner.")
async def edit_post(
    session: SessionDep,
    post_id: int,
    post_data: str = Form(...),  # Receives the JSON as a string
    file: UploadFile | None = File(None),  # Optional file upload
    current_user: User = Depends(get_current_user),  # Get current user
):
    try:
        # Convert the string post_data into a dictionary
        post_data_dict = json.loads(post_data)  # Convert the JSON string to a dictionary
        
        # Validate the post data using the Pydantic model
        validated_post_data = PostPatch.model_validate(post_data_dict)

        # Handle file upload
        file_url = None
        if file:
            # Validate and upload the new file (e.g., to Catbox)
            validated_file = await validate_file(file)
            if validated_file:
                file_url = await upload_to_catbox(validated_file)  # Upload the file and get the URL

        # Call the service method to update the post
        updated_post = post_service.patch_post(session, post_id, validated_post_data, current_user.id, file_url) # type: ignore

        return updated_post

    except NotOwnerError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except PostNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON data")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
