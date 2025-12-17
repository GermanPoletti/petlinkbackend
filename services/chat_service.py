# services/chat_service.py
from typing import List
from sqlmodel import Session, select, or_, desc, asc  # ← ESTOS SON LOS IMPORTS QUE FALTABAN
from datetime import datetime

# Modelos
from models.chat.chat import Chat
from models.chat.chat_message import ChatMessage
from models.post.post import Post
from models.user.user import User, UserProfiles

# Excepciones
from exceptions.exceptions import (
    PostNotFoundException,
    ChatNotFoundException,
    ChatAlreadyExistsException,
    ChatClosedException,
    NotOwnerError,
)

# Schemas y enums
from schemas.chats_schemas import ChatDetailRead, ChatFilters, ChatMessageRead
from models.enums import AgreementStatusEnum


def get_display_name(user: User | None) -> str:
    """
    Devuelve el nombre visible del usuario:
    - Si tiene username → username
    - Si no → el email completo (nico@gmail.com)
    - Si no hay nada → "Usuario desconocido"
    """
    if not user:
        return "Usuario desconocido"
    
    if user.user_info and user.user_info.username:
        return user.user_info.username
    
    return user.email

# ==================================================================
# 1. Crear un chat cuando alguien pulsa "Estoy interesado"
# ==================================================================
def create_chat(session: Session, post_id: int, initiator_user_id: int) -> Chat:
    post = session.get(Post, post_id)
    if not post or not post.is_active:
        raise PostNotFoundException()

    receiver_user_id = post.user_id

    if initiator_user_id == receiver_user_id:
        raise ValueError("No podés iniciar un chat con tu propia publicación")

    existing_chat = session.exec(
        select(Chat).where(
            Chat.post_id == post_id,
            Chat.initiator_id == initiator_user_id
        )
    ).first()

    if existing_chat:
        raise ChatAlreadyExistsException()

    new_chat = Chat(
        post_id=post_id,
        initiator_id=initiator_user_id,
        receiver_id=receiver_user_id,
        status_id=AgreementStatusEnum.PENDING,
        is_active=True
    )

    session.add(new_chat)
    session.commit()
    session.refresh(new_chat)
    return new_chat


# ==================================================================
# 2. Obtener todos los chats del usuario logueado
# ==================================================================
def get_user_chats(session: Session, user_id: int, filters: ChatFilters) -> List[Chat]:
    query = select(Chat).where(
        or_(
            Chat.initiator_id == user_id,
            Chat.receiver_id == user_id
        )
    )

    if filters.post_id:
        query = query.where(Chat.post_id == filters.post_id)

    if filters.only_active is not None:
        query = query.where(Chat.is_active == filters.only_active)

    if filters.status_id is not None:
        query = query.where(Chat.status_id == filters.status_id)

    # Ahora sí: desc y asc están importados
    query = query.order_by(desc(Chat.updated_at))
    query = query.offset(filters.skip).limit(filters.limit)
    # query = query.where(Chat.status_id == AgreementStatusEnum.PENDING)
    return session.exec(query).all()   # type: ignore


# ==================================================================
# 3. Obtener el detalle completo de un chat
# ==================================================================
def get_chat_detail(session: Session, chat_id: int, requesting_user_id: int) -> ChatDetailRead:
    chat = session.get(Chat, chat_id)
    if not chat:
        raise ChatNotFoundException()

    if chat.initiator_id != requesting_user_id and chat.receiver_id != requesting_user_id:
        raise PermissionError("No tenés permiso para ver este chat")

    # Mensajes ordenados por fecha ascendente
    messages_raw = session.exec(
        select(ChatMessage)
        .where(ChatMessage.chat_id == chat_id)
        .order_by(asc(ChatMessage.created_at))  # ← importado correctamente
    ).all()

    # Convertir a ChatMessageRead (para que salga el sender_username)
    messages = [
        ChatMessageRead(
            id=msg.id, # type: ignore
            chat_id=msg.chat_id,
            sender_id=msg.sender_id,
            message=msg.message,
            created_at=msg.created_at,
            sender_username=get_display_name(msg.sender)
        )
        for msg in messages_raw
    ]

    # Perfiles de usuario
    initiator_profile = session.get(UserProfiles, chat.initiator_id)
    
    receiver_profile = session.get(UserProfiles, chat.receiver_id)
    return ChatDetailRead(
        **chat.model_dump(),
        post_title=chat.post.title if chat.post else None,
        initiator_username = (
        getattr(initiator_profile, "username", None) or 
        getattr(chat.initiator, "email", "Usuario desconocido")
        ), 
        receiver_username=(
        getattr(receiver_profile, "username", None) or 
        getattr(chat.receiver, "email", "Usuario desconocido")
        ),
        messages=messages  # ← ahora es List[ChatMessageRead]
    )


# ==================================================================
# 4. Enviar un mensaje
# ==================================================================
def send_message(
    session: Session,
    chat_id: int,
    sender_user_id: int,
    message_text: str
) -> ChatMessage:
    chat = session.get(Chat, chat_id)
    if not chat:
        raise ChatNotFoundException()
    if not chat.is_active:
        raise ChatClosedException()
    if chat.initiator_id != sender_user_id and chat.receiver_id != sender_user_id:
        raise PermissionError("No participás en este chat")

    new_message = ChatMessage(
        chat_id=chat_id,
        sender_id=sender_user_id,
        message=message_text.strip()
    )

    chat.updated_at = datetime.utcnow()

    session.add(new_message)
    session.add(chat)
    session.commit()
    session.refresh(new_message)
    return new_message


# ==================================================================
# 5. Cerrar el acuerdo: concretar o rechazar
# ==================================================================
def resolve_chat(
    session: Session,
    chat_id: int,
    requesting_user_id: int,
    completed: bool,
    resolution_note: str | None = None
) -> Chat:
    chat = session.get(Chat, chat_id)
    if not chat:
        raise ChatNotFoundException()
    if not chat.is_active:
        raise ChatClosedException("El chat ya está cerrado")
    if chat.receiver_id != requesting_user_id:
        raise NotOwnerError("Solo el dueño de la publicación puede cerrar el acuerdo")

    chat.status_id = AgreementStatusEnum.COMPLETED if completed else AgreementStatusEnum.REJECTED
    chat.is_active = False
    chat.closing_date = datetime.utcnow()
    chat.resolution_note = (resolution_note or "").strip()[:500] or None

    if completed:
        if chat.post.post_type_id == 2: # type: ignore
            initiator = session.get(User, chat.initiator_id)
            if initiator:
                initiator.help_count = (initiator.help_count or 0) + 1
                session.add(initiator)

        post = session.get(Post, chat.post_id)
        if post:
            post.is_active = False
            session.add(post)

    session.add(chat)
    session.commit()
    session.refresh(chat)
    return chat