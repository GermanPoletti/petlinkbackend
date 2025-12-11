from datetime import datetime, timezone
from fastapi import Depends, HTTPException
from pydantic import BaseModel, EmailStr, ValidationError
from sqlmodel import Session, func, select
from sqlalchemy.orm import joinedload

from models import User, enums
from models.user.user import UserProfiles
from models import StatusUserEnum
from schemas import UserRead, UserPatch

from services.auth_service import encrypt_password, terminate_active_session

from dependencies.auth_dependencies import get_current_user

from exceptions.exceptions import UserNotFoundException

# services/user_service.py
from datetime import date, datetime, time, timezone
from io import BytesIO
import pandas as pd
from fastapi import HTTPException, status
from sqlmodel import select
from sqlalchemy.orm import joinedload

from models.user.user import User
from models.enums import RoleEnum, StatusUserEnum
from core.database import SessionDep


def export_users_excel_service(date_from: date, date_to: date, session: SessionDep) -> BytesIO:
    # Convertir fechas a datetime con rango completo del día (UTC)
    start_dt = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(date_to, time.max, tzinfo=timezone.utc)

    users = session.exec(
        select(User)
        .options(joinedload(User.user_info))
        .where(User.created_at >= start_dt, User.created_at <= end_dt)
        .order_by(User.created_at)
    ).all()

    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron usuarios en ese rango de fechas"
        )

    data = []
    for user in users:
        profile = user.user_info
        data.append({
            "ID": user.id,
            "Email": user.email,
            "Nombre": profile.first_name if profile else None,
            "Apellido": profile.last_name if profile else None,
            "Username": profile.username if profile else None,
            "Rol": ("Administrador" if user.role_id == RoleEnum.ADMIN.value
                    else "Moderador" if user.role_id == RoleEnum.MODERATOR.value
                    else "Usuario"),
            "Estado": ("Activo" if user.status_id == StatusUserEnum.ACTIVE.value
                       else "Baneado" if user.status_id == StatusUserEnum.BANNED.value
                       else "Eliminado"),
            "Ayudas dadas": user.help_count,
            "Registrado": user.created_at.strftime("%d/%m/%Y %H:%M"),
            "Última actualización": user.updated_at.strftime("%d/%m/%Y %H:%M") if user.updated_at else "—",
        })

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Usuarios")

    output.seek(0)
    return output

class EmailCheck(BaseModel):
    email: EmailStr

def _mark_user_as_deleted(user: User, session: Session) -> dict[str, str]:

    user.status_id = enums.StatusUserEnum.DELETED
    user.deleted_at = datetime.now(timezone.utc)
    
    session.commit()
    return {"detail": "Usuario eliminado exitosamente"}

def count_all_users(session: Session):
    users = session.exec(select(func.count(User.id)).where(User.status_id == StatusUserEnum.ACTIVE)) # type: ignore
    count = users.first()
    return count

def get_user_by_role(session:Session, role:str):
    

    return session.exec(select(User).where(User.role_id == enums.RoleEnum[role].value)).all()



def patch_self(user_id: int, session: Session, user_data: UserPatch) -> UserRead:
    user = session.get(User, user_id) 
    
    if not user:
        raise UserNotFoundException(f"User with id {user_id} not found")

    update_data = user_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key in ["password", "email"]:
            if key == "password":
                #TODO: separate password change with another endpoint that sends a verification code
                value = encrypt_password(value)
                setattr(user, "password_hash", value)
                continue
            elif key == "email":
                if session.exec(select(User).where(User.email == value, User.id != user_id)).first():
                    raise ValueError("Email already exists")
            
            setattr(user, key, value)

        else:
            if user.user_info is None:
                user.user_info = UserProfiles(user_id=user_id)
                session.add(user.user_info)
            
            setattr(user.user_info, key, value)

    user.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(user) 

    return UserRead.model_validate(user)

def delete_self(user_id: int, session: Session) -> dict[str, str]:
    user = session.get(User, user_id)
    if not user:
        raise UserNotFoundException(f"User with id {user_id} not found")
    
    terminate_active_session(session = session, user_id = user_id)

    return _mark_user_as_deleted(user, session)

def get_all_users(session: Session) -> list[UserRead]:
    users = session.exec(select(User).options(joinedload(User.user_info))).all() # type: ignore
    
    return [UserRead.model_validate(u) for u in users]

def get_user_by_id(user_id: int, session: Session) -> UserRead:
    user = session.get(User, user_id, options=[joinedload(User.user_info)]) # type: ignore
    if not user:
        raise UserNotFoundException(f"User with id {user_id} not found")

    return UserRead.model_validate(user, from_attributes=True)

def patch_user(user_id: int, session: Session, role_id: enums.RoleEnum) -> dict[str, str]:
    user = session.exec(
        select(User).where(User.id == user_id)
    ).first()
    if not user:
        raise UserNotFoundException(f"User with id {user_id} not found")
    user.role_id = role_id
    session.commit()
    return {"detail": "rol de usuario actualizado exitosamente"}
    
def delete_user_by_admin(user_id: int, session: Session) -> dict[str, str]:
    user = session.get(User, user_id)
    if not user:
        raise UserNotFoundException(f"User with id {user_id} not found")
    
    terminate_active_session(session = session, user_id = user_id)

    return _mark_user_as_deleted(user, session)

