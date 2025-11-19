from datetime import datetime, timezone
from sqlmodel import Session, desc, func, select

from exceptions.exceptions import PostNotFoundException
from models import Like, Post, PostMultimedia, User, RoleEnum, City
from schemas import PostCreate, PostPatch, PostRead, PostFilters
from exceptions import NotOwnerError
from sqlalchemy.exc import SQLAlchemyError


def create_post(session: Session, payload: PostCreate, user_id: int):

    post_data = payload.model_dump(exclude={"multimedia"}, exclude_unset=True)
    post = Post(user_id=user_id, **post_data)
    session.add(post)
    session.commit()
    session.refresh(post)

    assert post.id is not None
    for mm in payload.multimedia:
        session.add(PostMultimedia(post_id=post.id, url=str(mm.url)))
    session.commit()
    session.refresh(post)

    return PostRead.model_validate(post)

def get_posts_by_user(session: Session, user_id: int) -> list[PostRead]:
    posts = session.exec(select(Post).where(Post.user_id == user_id)).all()
    
    return [PostRead.model_validate(p) for p in posts]

def get_posts(session: Session, filters: PostFilters, user: User):
    

    conditions = []
    skip, limit = filters.skip, filters.limit
    
    if user.role_id < RoleEnum.MODERATOR:
        conditions.append(Post.is_active == True)
    elif filters.show_only_active:
        conditions.append(Post.is_active == True)
    elif not filters.show_only_active:
        conditions.append(Post.is_active == False)

    if filters.category:
        conditions.append(Post.category == filters.category)

    if filters.city_id:
        conditions.append(Post.city_id == filters.city_id)

    if filters.province_id:
        conditions.append(City.state_province_id == filters.province_id)

    query = (
        select(Post, func.count(Like.id).label("likes_count")) #type: ignore
        .join(Like, Like.post_id == Post.id, isouter=True)  #type: ignore
        .join(City, City.id == Post.city_id)    # type: ignore
        .group_by(Post.id)  #type: ignore
    )

    if conditions:
        query = query.where(*conditions)

    if filters.most_liked:
        query = query.order_by(desc("likes_count"))

    posts_with_counts = session.exec(query.offset(skip).limit(limit)).all()

    # posts_with_counts trae: (Post, likes_count)
    posts = [p[0] for p in posts_with_counts]

    return [PostRead.model_validate(p) for p in posts]

def get_post_by_id(session: Session, post_id) -> PostRead:
    post = session.get(Post, post_id)
    if not post:
        raise PostNotFoundException
    return PostRead.model_validate(post)

def patch_post(session: Session, post_id: int, payload: PostPatch, user_id):
    payload_data = payload.model_dump(exclude={"multimedia"}, exclude_unset=True)
    post = session.get(Post, post_id)
    if not post:
        raise PostNotFoundException("Post does not exist")
    if post.user_id != user_id:
        raise NotOwnerError("Cannot edit the post, user is not the owner of the post")

    for key, value in payload_data.items():
        setattr(post, key, value)

    post.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(post)  
    return {"detail": "post edited successfully"}  

def delete_post(session: Session, post_id: int, user: User):
    user_id = user.id
    post = session.get(Post, post_id)

    if not post or not post.is_active:
        raise PostNotFoundException("Post doesn't exist or is already deleted")
    
    if post.user_id != user_id and user.role_id < RoleEnum.MODERATOR:
        raise NotOwnerError("Cannot delete, user is not owner of the post neither moderator or admin")


    post.is_active = False
    post.deleted_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(post)    
    return {"detail": "post deleted succesfully"}

def _give_like(session: Session, post_id: int, user_id: int):
    new_like = Like(post_id=post_id, user_id=user_id)
    session.add(new_like)

def _remove_like(session: Session, post_id: int, user_id: int):
    like = session.exec(
        select(Like).where(Like.post_id == post_id, Like.user_id == user_id)
    ).first()
    if like:
        session.delete(like)

def like_post(session: Session, post_id: int, user_id: int):
    post = session.get(Post, post_id)
    
    if not post or not post.is_active:
        raise PostNotFoundException("Post doesn't exist or is inactive")
    
    try:
        existing_like = session.exec(
            select(Like).where(Like.user_id == user_id, Like.post_id == post_id)
        ).first()
        if existing_like:
            _remove_like(session, post_id, user_id)
            detail = "like deleted"
        else:
            _give_like(session, post_id, user_id)
            detail = "like given"
        session.commit()
        return {"detail": detail}
    except SQLAlchemyError as e:
        session.rollback()
        raise e
 

def search_post(session: Session, keyword: str, skip: int = 0, limit: int = 10):
    if not keyword:
        return []  

    # construir query
    query = (
        select(Post)
        .where(
            Post.title.ilike(f"%{keyword}%") |   # type: ignore
            Post.message.ilike(f"%{keyword}%")  # type: ignore
        )
        .offset(skip)
        .limit(limit)
    )

    posts = session.exec(query).all()

    # si usas Pydantic / PostRead
    return [PostRead.model_validate(p) for p in posts]
