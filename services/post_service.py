from datetime import datetime, timezone
from sqlmodel import Session, desc, func, select

from exceptions.exceptions import PostNotFoundException
from models import Like, Post, PostMultimedia, User, RoleEnum, City
from models.location.state_province import StateProvince
from schemas import PostCreate, PostPatch, PostRead, PostFilters
from exceptions import NotOwnerError
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.orm import selectinload, joinedload


def get_city_id_by_name(city_name: str, session) -> int:
    """
    Busca el ID de una ciudad por nombre (case-insensitive)
    y asegura que pertenezca a la provincia 'Buenos Aires'
    """
    statement = (
        select(City.id)
        .join(StateProvince)
        .where(
            City.name.ilike(city_name.strip()),  # type: ignore
            StateProvince.name.ilike("Buenos Aires")  # type: ignore
        )
    )

    result = session.exec(statement)

    try:
        city_id: int = result.one()
        return city_id
    except NoResultFound:
        raise ValueError(f"Ciudad '{city_name}' no encontrada en la provincia de Buenos Aires")


def _resolve_display_name(post: Post) -> str:
    """Devuelve el texto de ubicación más específico disponible para un post."""
    if post.location_text:
        return post.location_text
    if post.city and post.city.state_province:
        return f"{post.city.name}, {post.city.state_province.name}"
    if post.city:
        return post.city.name
    return "Sin ubicación"


def _resolve_username(post: Post) -> str:
    return (
        getattr(getattr(getattr(post, "user", None), "user_info", None), "username", None)
        or getattr(getattr(post, "user", None), "email", "Usuario eliminado")
    )


def create_post(session: Session, payload: PostCreate, user_id: int, file_url: str | None):
    city_id: int | None = None

    if payload.city_name:
        try:
            city_id = get_city_id_by_name(payload.city_name, session)
        except ValueError:
            # Ciudad no encontrada en Georef → continúa sin city_id
            # El post usará location_text / coordenadas como referencia
            city_id = None

    post_data = payload.model_dump(
        exclude={"city_name"},
        exclude_unset=True,
        exclude_none=False,
    )
    # Asignar city_id resuelto (puede ser None)
    post_data["city_id"] = city_id

    post = Post(user_id=user_id, **post_data)
    session.add(post)
    session.commit()
    session.refresh(post)

    if file_url:
        session.add(PostMultimedia(post_id=post.id, url=file_url))  # type: ignore
        session.commit()

    session.refresh(post)
    return PostRead.model_validate(post)


def is_liked_by_user(session: Session, post_id: int, user_id: int):
    like = session.exec(
        select(Like).where(Like.post_id == post_id).where(Like.user_id == user_id)
    ).first()
    return bool(like)


def get_posts_by_user(session: Session, user_id: int) -> list[PostRead]:
    posts = session.exec(select(Post).where(Post.user_id == user_id)).all()
    return [PostRead.model_validate(p) for p in posts]


def get_posts(session: Session, filters: PostFilters, user: User):
    conditions = []
    skip, limit = filters.skip, filters.limit

    if filters.show_only_active is True:
        conditions.append(Post.is_active == True)
    elif filters.show_only_active is False:
        conditions.append(Post.is_active == False)
    # show_only_active is None → sin filtro

    if filters.category:
        conditions.append(Post.category == filters.category)

    if filters.city:
        conditions.append(City.name.ilike(f"%{filters.city}%"))  # type: ignore

    if filters.user_id:
        conditions.append(Post.user_id == filters.user_id)

    if filters.province_id:
        conditions.append(City.state_province_id == filters.province_id)

    if filters.post_type_id is not None:
        conditions.append(Post.post_type_id == filters.post_type_id)

    if filters.keyword:
        keyword = f"%{filters.keyword}%"
        conditions.append(
            (Post.title.ilike(keyword)) | (Post.message.ilike(keyword))  # type: ignore
        )

    # --- Filtro geográfico por radio (Haversine via ST_Distance_Sphere) ---
    # ST_Distance_Sphere(POINT(lon, lat), POINT(lon, lat)) devuelve metros en MySQL 5.7+
    # Solo aplica a posts que tengan coordenadas cargadas.
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
            joinedload(Post.city),  # type: ignore
            joinedload(Post.user).joinedload(User.user_info),  # type: ignore
            selectinload(Post.multimedia),  # type: ignore
            selectinload(Post.likes),  # type: ignore
        )
        # outerjoin: posts sin city_id (solo coordenadas) también se incluyen
        .outerjoin(City, City.id == Post.city_id)  # type: ignore
        .join(User, User.id == Post.user_id)  # type: ignore
        .outerjoin(Like, Like.post_id == Post.id)  # type: ignore
    )

    if conditions:
        query = query.where(*conditions)

    if filters.most_liked:
        query = query.order_by(desc(func.count(Like.id)))  # type: ignore
    else:
        query = query.order_by(Post.created_at.desc())  # type: ignore

    posts = session.exec(query.offset(skip).limit(limit)).all()

    result = []
    for post in posts:
        validated = PostRead.model_validate(post)
        validated = validated.model_copy(update={
            "likes_count": len(post.likes) if post.likes else 0,
            "city_name": _resolve_display_name(post),
            "username": _resolve_username(post),
            "latitude": post.latitude,
            "longitude": post.longitude,
            "location_text": post.location_text,
        })
        result.append(validated)

    return result


def get_post_by_id(session: Session, post_id) -> PostRead:
    post = session.get(Post, post_id)
    if not post:
        raise PostNotFoundException

    validated = PostRead.model_validate(post)
    validated = validated.model_copy(update={
        "likes_count": len(post.likes),
        "city_name": _resolve_display_name(post),
        "username": _resolve_username(post),
        "latitude": post.latitude,
        "longitude": post.longitude,
        "location_text": post.location_text,
    })
    return validated


def patch_post(session: Session, post_id: int, payload: PostPatch, user_id: int, file_url: str | None = None):
    payload_data = payload.model_dump(exclude={"multimedia"}, exclude_unset=True)

    post = session.get(Post, post_id)
    if not post:
        raise PostNotFoundException("El post no existe")

    if post.user_id != user_id:
        raise NotOwnerError("No puedes editar este post porque no eres el propietario")

    # Si el patch incluye city_name, resolverlo a city_id
    city_name = payload_data.pop("city_name", None)
    if city_name:
        try:
            payload_data["city_id"] = get_city_id_by_name(city_name, session)
        except ValueError:
            pass  # city_name no resuelto → se mantiene el city_id previo

    for key, value in payload_data.items():
        setattr(post, key, value)

    if file_url and len(post.multimedia) > 0:
        post.multimedia[0].url = file_url
    elif file_url and len(post.multimedia) == 0:
        post.multimedia.append(PostMultimedia(post_id=post_id, url=file_url))

    post.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(post)

    return {"detail": "Post editado exitosamente", "post": post}


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


def search_post(session: Session, keyword: str, skip: int = 0, limit: int = 10) -> list[PostRead]:
    if not keyword:
        return []

    query = (
        select(Post)
        .where(
            Post.title.ilike(f"%{keyword}%") |  # type: ignore
            Post.message.ilike(f"%{keyword}%")  # type: ignore
        )
        .offset(skip)
        .limit(limit)
    )

    posts = session.exec(query).all()
    return [PostRead.model_validate(p) for p in posts]
