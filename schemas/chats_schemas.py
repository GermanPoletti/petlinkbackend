from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field as PydanticField
from enum import IntEnum

from schemas.user_schemas import UserRead


class AgreementStatusEnum(IntEnum):
    PENDING = 1
    REJECTED = 2
    COMPLETED = 3



class ChatBase(BaseModel):
    post_id: int
    



class ChatCreate(ChatBase):
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "post_id": 45
                }
            ]
        }
    }



class ChatResolve(BaseModel):
    completed: bool = PydanticField(
        description="True → acuerdo concretado (COMPLETED + post inactivo), False → rechazado (REJECTED)"
    )
    resolution_note: Optional[str] = PydanticField(
        default=None,
        max_length=500,
        description="Motivo del rechazo o comentario final (opcional)"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "completed": True,
                    "resolution_note": "Se concretó la venta en persona"
                },
                {
                    "completed": False,
                    "resolution_note": "El comprador nunca respondió"
                }
            ]
        }
    }


class ChatRead(ChatBase):
    id: int
    initiator_id: int
    receiver_id: int
    status_id: AgreementStatusEnum
    closing_date: Optional[datetime] = None
    resolution_note: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChatReadWithUser(ChatRead):
    initiator: Optional[UserRead] = None
    receiver: Optional[UserRead] = None
# ------------------------------------------------------------------
# 4. Chat completo (con post, usuarios y mensajes) → para el detalle
# ------------------------------------------------------------------
class ChatDetailRead(ChatRead):
    # Podés incluir aquí los objetos completos si querés, o solo IDs
    # Yo te dejo solo lo más usado, pero podés expandirlo fácil
    post_title: Optional[str] = None          # si querés evitar JOIN en el frontend
    initiator_username: Optional[str] = None
    receiver_username: Optional[str] = None

    messages: List["ChatMessageRead"] = []

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Mensajes del chat
# ------------------------------------------------------------------
class ChatMessageBase(BaseModel):
    message: str = PydanticField(..., min_length=1, max_length=2000)


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageRead(ChatMessageBase):
    id: int
    chat_id: int
    sender_id: int
    created_at: datetime

    # Opcional: nombre del que envió (para no hacer JOIN en el frontend)
    sender_username: Optional[str] = None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# Filtro para listar chats del usuario logueado
# ------------------------------------------------------------------
class ChatFilters(BaseModel):
    post_id: int | None = None
    only_active: Optional[bool] = None     # None = todos, True = solo abiertos, False = solo cerrados
    status_id: Optional[AgreementStatusEnum] = None
    skip: int = 0
    limit: int = 20

    model_config = {"from_attributes": True}