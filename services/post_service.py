from datetime import datetime, timezone
from sqlmodel import Session, desc, func, select

from exceptions.exceptions import PostNotFoundException
from models import Like, Post, PostMultimedia, User, RoleEnum
from schemas import PostCreate, PostPatch, PostRead, PostFilters
from exceptions import NotOwnerError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload, joinedload


def _resolve_username(post: Post) -> str:
    return (
        getattr(getattr(getattr(post, "user", None), "user_info", None), "username", None)
        or getattr(getattr(post, "user", None), "email", "Usuario eliminado")
    )


def create_post(session: Session, payload: PostCreate, user_id: int, file_url: str | None):
    post_data = payload.model_dump(exclude_unset=True)
    post = Post(user_id=user_id, **post_data)
    session.add(post)
    session.commit()
    session.refresh(post)

    if file_url:
        session.add(PostMultimedia(post_id=post.id, url=file_url))  # type: ignore
        session.commit()
        session.refresh(post)

    validated = PostRead.model_validate(post)
    validated = validated.model_copy(update={
        "city_name": post.location_text or "Sin ubicación",
        "username": _resolve_username(post),
    })
    return validated


def is_liked_by_user(session: Session, post_id: int, user_id: int) -> bool:
    like = session.exec(
        select(Like).where(Like.post_id == post_id, Like.user_id == user_id)
    ).first()
    return bool(like)


def get_posts_by_user(session: Session, user_id: int) -> list[PostRead]:
    posts = session.exec(
        select(Post).where(Post.user_id == user_id).order_by(desc(Post.created_at))
    ).all()
    result = []
    for post in posts:
        validated = PostRead.model_validate(post)
        validated = validated.model_copy(update={
            "city_name": post.location_text or "Sin ubicación",
            "username": _resolve_username(post),
        })
        result.append(validated)
    return result


def get_posts(session: Session, filters: PostFilters, user: User) -> list[PostRead]:
    conditions = []

    if filters.show_only_active is True:
        conditions.append(Post.is_active == True)
    elif filters.show_only_active is False:
        conditions.append(Post.is_active == False)

    if filters.category:
        conditions.append(Post.category == filters.category)

    if filters.user_id:
        conditions.append(Post.user_id == filters.user_id)

    if filters.post_type_id is not None:
        conditions.append(Post.post_type_id == filters.post_type_id)

    if filters.keyword:
        kw = f"%{filters.keyword}%"
        conditions.append(
            (Post.title.ilike(kw)) | (Post.message.ilike(kw))  # type: ignore
        )

    # Filtro geográfico por radio usando ST_Distance_Sphere (MySQL 5.7+)
    # Solo se aplica a posts que tengan coordenadas cargadas.
    # ST_Distance_Sphere devuelve distancia en metros; radius_km * 1000 = metros.
    if filters.lat is not None and filters.lon is not None:
        radius_m = filters.radius_km * 1000
        distance_expr = func.ST_Distance_Sphere(
            func.POINT(filters.lon, filters.lat),
            func.POINT(Post.longitude, Post.latitude),
        )
        conditions.append(Post.latitude.isnot(None))   # type: ignore
        conditions.append(Post.longitude.isnot(None))  # type: ignore
        conditions.append(distance_expr <= radius_m)

    query = (
        select(Post)
        .distinct(Post.id)  # type: ignore
        .options(
            joinedload(Post.user).joinedload(User.user_info),  # type: ignore
            selectinload(Post.multimedia),  # type: ignore
            selectinload(Post.likes),  # type: ignore
        )
        .join(User, User.id == Post.user_id)  # type: ignore
        .outerjoin(Like, Like.post_id == Post.id)  # type: ignore
    )

    if conditions:
        query = query.where(*conditions)

    # most_liked=True is the legacy param; sort_by takes precedence when set
    effective_sort = 'most_liked' if filters.most_liked else filters.sort_by
    
    if effective_sort == 'most_liked':
        query = (
            query.group_by(Post.id)  # <-- ¡ESTO EVITA EL ERROR 500 EN MYSQL!
            .order_by(desc(func.count(Like.id)))
        )
    elif effective_sort == 'closest' and filters.lat is not None and filters.lon is not None:
        dist_sort = func.ST_Distance_Sphere(
            func.POINT(filters.lon, filters.lat),
            func.POINT(Post.longitude, Post.latitude),
        )
        query = query.order_by(dist_sort.asc())  # type: ignore
    else:
        # Si elegimos ordenar por los más nuevos, agrupamos también por las dudas
        # ya que la query tiene un join con likes que podría duplicar filas sin group_by
        query = query.group_by(Post.id).order_by(Post.created_at.desc())  # type: ignore

    posts = session.exec(query.offset(filters.skip).limit(filters.limit)).all()

    result = []
    for post in posts:
        validated = PostRead.model_validate(post)
        validated = validated.model_copy(update={
            "likes_count": len(post.likes) if post.likes else 0,
            "city_name": post.location_text or "Sin ubicación",
            "username": _resolve_username(post),
        })
        result.append(validated)
    return result


def get_post_by_id(session: Session, post_id: int) -> PostRead:
    post = session.get(Post, post_id)
    if not post:
        raise PostNotFoundException

    validated = PostRead.model_validate(post)
    validated = validated.model_copy(update={
        "likes_count": len(post.likes),
        "city_name": post.location_text or "Sin ubicación",
        "username": _resolve_username(post),
    })
    return validated


def patch_post(session: Session, post_id: int, payload: PostPatch, user_id: int, file_url: str | None = None):
    payload_data = payload.model_dump(exclude={"multimedia"}, exclude_unset=True)

    post = session.get(Post, post_id)
    if not post:
        raise PostNotFoundException("El post no existe")

    if post.user_id != user_id:
        raise NotOwnerError("No puedes editar este post porque no eres el propietario")

    for key, value in payload_data.items():
        setattr(post, key, value)

    if file_url and len(post.multimedia) > 0:
        post.multimedia[0].url = file_url
    elif file_url:
        post.multimedia.append(PostMultimedia(post_id=post_id, url=file_url))

    post.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(post)

    return {"detail": "Post editado exitosamente", "post": post}


def delete_post(session: Session, post_id: int, user: User):
    post = session.get(Post, post_id)

    if not post or not post.is_active:
        raise PostNotFoundException("Post doesn't exist or is already deleted")

    if post.user_id != user.id and user.role_id < RoleEnum.MODERATOR:
        raise NotOwnerError("Cannot delete, user is not owner of the post neither moderator or admin")

    post.is_active = False
    post.deleted_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(post)
    return {"detail": "post deleted succesfully"}


def _give_like(session: Session, post_id: int, user_id: int):
    session.add(Like(post_id=post_id, user_id=user_id))


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
        existing = session.exec(
            select(Like).where(Like.user_id == user_id, Like.post_id == post_id)
        ).first()
        if existing:
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


def search_post(session: Session, keyword: str, skip: int = 0, limit: int = 10) -> list[PostRead]:
    if not keyword:
        return []

    posts = session.exec(
        select(Post)
        .where(
            Post.title.ilike(f"%{keyword}%") |  # type: ignore
            Post.message.ilike(f"%{keyword}%")  # type: ignore
        )
        .offset(skip)
        .limit(limit)
    ).all()

    return [PostRead.model_validate(p) for p in posts]
