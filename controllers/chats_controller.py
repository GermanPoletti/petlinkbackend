from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Path, Query
from sqlmodel import select, desc

from core.database import SessionDep
from dependencies.auth_dependencies import get_current_user
from models.user.user import User
from models.chat.chat import Chat
from models.chat.chat_message import ChatMessage
from models.post.post import Post
from schemas.chats_schemas import (
    ChatCreate, ChatReadWithUser, ChatResolve, ChatRead, ChatDetailRead,
    ChatMessageCreate, ChatMessageRead, ChatFilters
)
from services import chat_service
from services import push_notification_service
from exceptions.exceptions import (
    NotOwnerError, PostNotFoundException,
    ChatNotFoundException, ChatAlreadyExistsException,
    ChatClosedException
)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatRead)
def create_chat(
    session: SessionDep,
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user)
):
    try:
        return chat_service.create_chat(
            session=session,
            post_id=chat_data.post_id,
            initiator_user_id=current_user.id # type: ignore
        )
    except PostNotFoundException:
        raise HTTPException(status_code=404, detail="Publicación no encontrada o no está activa")
    except ChatAlreadyExistsException:
        raise HTTPException(status_code=409, detail="Ya tienes un chat abierto con esta publicación")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # ← ESTE ES EL QUE TE ESTÁ MATANDO
        raise HTTPException(status_code=400, detail=f"Error inesperado: {str(e)}")


# ------------------------------------------------------------------
# 2. Mis chats (abiertos y cerrados)
# ------------------------------------------------------------------
@router.get("/me", response_model=list[ChatReadWithUser])
def get_my_chats(
    session: SessionDep,
    filters: Annotated[ChatFilters, Query()],
    current_user: User = Depends(get_current_user)
):
    """
    Devuelve todos los chats donde el usuario es initiator o receiver.
    """
    chats = chat_service.get_user_chats(
        session=session,
        user_id=current_user.id, # type: ignore
        filters=filters
    )
    chats_with_users = []
    for chat in chats:
        counterpart_id = chat.receiver_id if chat.initiator_id == current_user.id else chat.initiator_id
        counterpart = session.get(User, counterpart_id)
        if not counterpart:
            continue

        last_msg = session.exec(
            select(ChatMessage)
            .where(ChatMessage.chat_id == chat.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(1)
        ).first()

        last_message = None
        if last_msg:
            sender = session.get(User, last_msg.sender_id)
            sender_name = (
                getattr(getattr(sender, "user_info", None), "username", None)
                or getattr(sender, "email", "Usuario")
            ) if sender else "Usuario"
            last_message = ChatMessageRead(
                id=last_msg.id,
                chat_id=last_msg.chat_id,
                sender_id=last_msg.sender_id,
                message=last_msg.message,
                created_at=last_msg.created_at,
                sender_username=sender_name,
            )

        unread_count = 1 if last_msg and last_msg.sender_id != current_user.id else 0

        chat_data = ChatReadWithUser(
            **chat.model_dump(),
            initiator=None,
            receiver=counterpart, # type: ignore
            last_message=last_message,
            unread_count=unread_count,
        )
        chats_with_users.append(chat_data)

    return chats_with_users


# ------------------------------------------------------------------
# 3. Detalle de un chat específico (con mensajes)
# ------------------------------------------------------------------
@router.get("/{chat_id}", response_model=ChatDetailRead)
def get_chat_detail(
    session: SessionDep,
    chat_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user)
):
    """
    Solo los participantes del chat pueden verlo.
    """
    try:
        return chat_service.get_chat_detail(
            session=session,
            chat_id=chat_id,
            requesting_user_id=current_user.id # type: ignore
        )
    except ChatNotFoundException:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    except PermissionError:
        raise HTTPException(status_code=403, detail="No tenés permiso para ver este chat")


# ------------------------------------------------------------------
# 4. Enviar mensaje
# ------------------------------------------------------------------
@router.post("/{chat_id}/messages", response_model=ChatMessageRead)
def send_message(
    session: SessionDep,
    message_data: ChatMessageCreate,
    background_tasks: BackgroundTasks,
    chat_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user)
):
    try:
        msg = chat_service.send_message(
            session=session,
            chat_id=chat_id,
            sender_user_id=current_user.id, # type: ignore
            message_text=message_data.message
        )
        background_tasks.add_task(
            push_notification_service.notify_chat_recipient,
            chat_id=chat_id,
            sender_id=current_user.id,
            message_preview=message_data.message.strip()[:100],
        )
        return msg
    except ChatNotFoundException:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    except ChatClosedException:
        raise HTTPException(status_code=403, detail="No se puede enviar mensajes a un chat cerrado")
    except PermissionError:
        raise HTTPException(status_code=403, detail="No participás en este chat")


# ------------------------------------------------------------------
# 5. Resolver chat: concretar o rechazar (solo el dueño del post)
# ------------------------------------------------------------------
@router.patch("/{chat_id}/resolve", response_model=ChatRead)
def resolve_chat(
    session: SessionDep,
    resolve_data: ChatResolve,
    chat_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user)
):
    """
    - completed=True  → status=COMPLETED + post.is_active=False
    - completed=False → status=REJECTED
    Solo el receiver (dueño del post) puede resolver.
    """
    try:
        return chat_service.resolve_chat(
            session=session,
            chat_id=chat_id,
            requesting_user_id=current_user.id, # type: ignore
            completed=resolve_data.completed,
            resolution_note=resolve_data.resolution_note
        )
    except ChatNotFoundException:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    except NotOwnerError:
        raise HTTPException(status_code=403, detail="Solo el dueño de la publicación puede cerrar el acuerdo")
    except ChatClosedException:
        raise HTTPException(status_code=409, detail="El chat ya está cerrado")