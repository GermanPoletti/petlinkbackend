"""
from fastapi import APIRouter, Depends

from core.database import SessionDep 
from dependencies.auth_dependencies import get_current_user
from models import User

router = APIRouter(prefix="/chats")

def initialize_chat(session: SessionDep, current_user: User = Depends(get_current_user)):
    pass

def send_message(session: SessionDep, current_user: User = Depends(get_current_user)):
    pass

def edit_message(session: SessionDep, current_user: User = Depends(get_current_user)):
    pass

def delete_message(session: SessionDep, current_user: User = Depends(get_current_user)):
    pass

def close_chat(session: SessionDep, current_user: User = Depends(get_current_user)):
    pass

def get_messages(session: SessionDep, current_user: User = Depends(get_current_user)):
    pass

def get_chats(session: SessionDep, current_user: User = Depends(get_current_user)):
    pass

"""

# routers/chat_router.py
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query

from core.database import SessionDep
from dependencies.auth_dependencies import get_current_user
from models.user.user import User
from models.chat.chat import Chat
from models.post.post import Post
from schemas.chats_schemas import (
    ChatCreate, ChatResolve, ChatRead, ChatDetailRead,
    ChatMessageCreate, ChatMessageRead, ChatFilters
)
from services import chat_service
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
            initiator_user_id=current_user.id
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
@router.get("/me", response_model=list[ChatRead])
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
        user_id=current_user.id,
        filters=filters
    )
    return chats


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
            requesting_user_id=current_user.id
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
    chat_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user)
):
    try:
        return chat_service.send_message(
            session=session,
            chat_id=chat_id,
            sender_user_id=current_user.id,
            message_text=message_data.message
        )
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
            requesting_user_id=current_user.id,
            completed=resolve_data.completed,
            resolution_note=resolve_data.resolution_note
        )
    except ChatNotFoundException:
        raise HTTPException(status_code=404, detail="Chat no encontrado")
    except NotOwnerError:
        raise HTTPException(status_code=403, detail="Solo el dueño de la publicación puede cerrar el acuerdo")
    except ChatClosedException:
        raise HTTPException(status_code=409, detail="El chat ya está cerrado")