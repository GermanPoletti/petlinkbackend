from datetime import datetime, timezone
from sqlmodel import Session, select

from exceptions.exceptions import PostNotFoundException
from models import Like, Post, PostMultimedia
from models.enums import RoleEnum
from models.user.user import User
from schemas import PostCreate, PostPatch, PostRead 
from exceptions import NotOwnerError
from sqlalchemy.exc import SQLAlchemyError

#TODO: cant like a inactive post
#TODO: separar gets para q un admin traiga todos y un user solo activos
#TODO: get para publicaciones de un usuario especifico



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


#TODO: return conteo de likes por post, usar model_validate
def get_posts(session: Session, skip: int = 0, limit: int = 10):
    posts = session.exec(
        select(Post).offset(skip).limit(limit)
    ).all()
    
    return posts

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
    
    if post.user_id != user_id and user.role_id != RoleEnum.ADMIN:
        raise NotOwnerError("Cannot delete, user is not owner of the post neither admin")


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
    if(session.get(Post, post_id)):
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
    else:
        raise PostNotFoundException("Post not found")
