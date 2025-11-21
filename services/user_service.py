from datetime import datetime, timezone
from fastapi import Depends
from pydantic import BaseModel, EmailStr, ValidationError
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload

from models import User, enums
from models.user.user import UserProfiles
from schemas import UserRead, UserPatch

from services.auth_service import encrypt_password, terminate_active_session

from dependencies.auth_dependencies import get_current_user

from exceptions.exceptions import UserNotFoundException



class EmailCheck(BaseModel):
    email: EmailStr

def _mark_user_as_deleted(user: User, session: Session) -> dict[str, str]:

    user.status_id = enums.StatusUserEnum.DELETED
    user.deleted_at = datetime.now(timezone.utc)
    
    session.commit()
    return {"detail": "Usuario eliminado exitosamente"}

# def patch_self(user_id: int, session: Session, user_data: UserPatch) -> UserRead:
#     user = session.get(User, user_id)
#     update_data = user_data.model_dump(exclude_unset=True)

#     if not user:
#         raise UserNotFoundException(f"User with id {user_id} not found")

#     for key, value in update_data.items():

#         if getattr(user, key) == value:
#             continue
        
#         elif key == "password":
#             #TODO: separate password change with another endpoint that sends a verification code
#             value = encrypt_password(value)
#         elif key == "email":
#             try:
#                 EmailCheck(email=value)
#             except ValidationError:
#                 raise ValueError(f"{value} no es un email válido")
            
#             if session.exec(select(User).where(User.email == value)).first():
#                 raise ValueError("Email already exists")
    
#         setattr(user.user_info, key, value)
    
#     user.updated_at = datetime.now(timezone.utc)
#     session.commit()
#     session.refresh(user)
    
#     return UserRead.model_validate(user, from_attributes=True)

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
    session.refresh(user)  # recarga todo con los nuevos valores

    # Aquí está la magia: SQLModel combina automáticamente User + UserProfiles
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

