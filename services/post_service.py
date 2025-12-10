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
            City.name.ilike(city_name.strip()), # type: ignore
            StateProvince.name.ilike("Buenos Aires") # type: ignore
        )
    )

    result = session.exec(statement)
    
    try:
        city_id: int = result.one()
        return city_id
    except NoResultFound:
        raise ValueError(f"Ciudad '{city_name}' no encontrada en la provincia de Buenos Aires")

def create_post(session: Session, payload: PostCreate, user_id: int, file_url: str | None):
    # resolver city_id
    if payload.city_name:
        try:
            city_id = get_city_id_by_name(payload.city_name, session)
        except ValueError as e:
            raise Exception(str(e))
    else:
        city_id = payload.city_id # type: ignore

    post_data = payload.model_dump(
        exclude={"city_name", "city_id"},
        exclude_unset=True
    )
    post_data["city_id"] = city_id

    post = Post(user_id=user_id, **post_data)
    session.add(post)
    session.commit()
    session.refresh(post)

    if file_url:
        session.add(PostMultimedia(post_id=post.id, url=file_url)) # type: ignore
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
    else:
        if filters.show_only_active is True:
            conditions.append(Post.is_active == True)
        elif filters.show_only_active is False:
            conditions.append(Post.is_active == False)

    if filters.category:
        conditions.append(Post.category == filters.category)

    if filters.city:
        conditions.append(City.name.ilike(f"%{filters.city}%")) # type: ignore

    if filters.user_id:
        conditions.append(Post.user_id == filters.user_id)

    if filters.province_id:
        conditions.append(City.state_province_id == filters.province_id)

    if filters.post_type_id is not None:
        conditions.append(Post.post_type_id == filters.post_type_id)

    # NUEVO: BÚSQUEDA POR PALABRA CLAVE
    if filters.keyword:
        keyword = f"%{filters.keyword}%"
        conditions.append(
            (Post.title.ilike(keyword)) | (Post.message.ilike(keyword)) # type: ignore
        )

    query = (
        select(Post)
        .distinct(Post.id) # type: ignore
        .options(
            joinedload(Post.city), # type: ignore
            joinedload(Post.user).joinedload(User.user_info), # type: ignore
            selectinload(Post.multimedia), # type: ignore
            selectinload(Post.likes) # type: ignore
        )
        .join(City, City.id == Post.city_id) # type: ignore
        .join(User, User.id == Post.user_id) # type: ignore
        .outerjoin(Like, Like.post_id == Post.id) # type: ignore
    )

    if conditions:
        query = query.where(*conditions)

    if filters.most_liked:
        query = query.order_by(desc(func.count(Like.id))) # type: ignore
    else:
        query = query.order_by(Post.created_at.desc()) # type: ignore

    posts = session.exec(query.offset(skip).limit(limit)).all()
    
    # INYECTAR likes_count y city_name MANUALMENTE
    result = []
    for post in posts:
        likes_count = len(post.likes) if post.likes else 0

        if post.city and post.city.state_province:
            city_name = f"{post.city.name}, {post.city.state_province.name}"
        elif post.city:
            city_name = post.city.name
        else:
            city_name = "Sin ubicación"    

        if post.user and post.user.user_info and post.user.user_info.username:
            username = post.user.user_info.username
        elif post.user and not post.user.user_info:
            username = post.user.email
         

        validated = PostRead.model_validate(post)
        validated = validated.model_copy(update={
            "likes_count": likes_count,
            "city_name": city_name if post.city else "Sin ubicación",  # ← ahora post.city SÍ existe
            "username": (
                getattr(getattr(getattr(post, "user", None), "user_info", None), "username", None)
                or getattr(getattr(post, "user", None), "email", "Usuario eliminado")
            )
        })
        result.append(validated)

    return result

def get_post_by_id(session: Session, post_id) -> PostRead:
    post = session.get(Post, post_id)
    if not post:
        raise PostNotFoundException
    return PostRead.model_validate(post)

def patch_post(session: Session, post_id: int, payload: PostPatch, user_id: int, file_url: str | None = None):
    # Convierte el payload en un diccionario, excluyendo el campo multimedia
    payload_data = payload.model_dump(exclude={"multimedia"}, exclude_unset=True)
    
    # Recupera el post de la base de datos
    post = session.get(Post, post_id)
    if not post:
        raise PostNotFoundException("El post no existe")
    
    # Verifica que el usuario sea el propietario del post
    if post.user_id != user_id:
        raise NotOwnerError("No puedes editar este post porque no eres el propietario")

    # Actualiza los campos del post con los nuevos valores
    for key, value in payload_data.items():
        setattr(post, key, value)

    # Si se proporcionó una nueva URL de archivo (es decir, un nuevo archivo), actualiza el campo image_url
    if file_url and len(post.multimedia) >0:
        post.multimedia[0].url = file_url
    elif file_url and len(post.multimedia) == 0:
        post.multimedia.append(PostMultimedia(post_id = post_id, url = file_url))

    # Establece la fecha de actualización
    post.updated_at = datetime.now(timezone.utc)

    # Guarda los cambios en la base de datos
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
