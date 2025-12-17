from datetime import date
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status, Query
from fastapi.responses import StreamingResponse
from core.database import SessionDep
from dependencies.auth_dependencies import get_current_user
from dependencies.permissions_dependencies import require_role
from exceptions.exceptions import UserNotFoundException
from models.enums import RoleEnum, StatusUserEnum
from models.user.user import User
from schemas.user_schemas import UserPatch, UserRead
from services import user_service
from sqlalchemy.orm import joinedload

from utils.generics import count_rows

#TODO: gestionar excepciones y respuestas http



router = APIRouter(prefix="/users", tags=["users"])

def _check_user_is_active(user: User | None = None, user_id: int | None = None, session: SessionDep | None = None):

    if (user is None and user_id is None) or (user is not None and user_id is not None):
        raise ValueError("You have to give either user or user_id")
    
    if(user_id and not session):
        raise ValueError("Session parameter requiered")


    if(user):
        return True if user.status_id == StatusUserEnum.ACTIVE else False
    elif(user_id and session):
        return True if user_service.get_user_by_id(user_id = user_id, session = session).status_id == StatusUserEnum.ACTIVE else False 
        

@router.get("/")
def get_all_users(session: SessionDep, current_user: User = require_role(RoleEnum.MODERATOR)):
    return user_service.get_all_users(session=session, user = current_user)


@router.get("/export/excel")
def export_users_to_excel(
    session: SessionDep,
    request: Request,  # ← AÑADIMOS ESTO
    date_from: date = Query(..., description="Fecha desde (YYYY-MM-DD)"),
    date_to: date = Query(..., description="Fecha hasta (YYYY-MM-DD)"),
    current_user: User = require_role(RoleEnum.ADMIN),
):
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="La fecha inicial no puede ser mayor que la final")

    excel_file = user_service.export_users_excel_service(date_from, date_to, session)

    filename = f"usuarios_{date_from}_a_{date_to}.xlsx"

    # TRUCO MÁGICO para que descargue en el navegador real
    user_agent = request.headers.get("user-agent", "").lower()
    
    if "mozilla" in user_agent or "chrome" in user_agent or "safari" in user_agent:
        # Es un navegador → forzamos descarga
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Access-Control-Expose-Headers": "Content-Disposition",  # importante para CORS si usas frontend
            }
        )
    else:
        # Es Swagger/Postman → devolvemos normal (para que no se quebre)
        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )


@router.get("/ranking")
def get_user_rank(session: SessionDep,current_user: User = Depends(get_current_user)):
    return user_service.get_user_rank(session = session, user_id = current_user.id)

@router.get("/role")
def get_user_by_role(role: str ,session: SessionDep, current_user: User = require_role(RoleEnum.MODERATOR) ):
    return user_service.get_user_by_role(session=session, role = role)

@router.get("/count")
def get_users_count(session: SessionDep, current_user: User = require_role(RoleEnum.MODERATOR)):
    filters = {
        "status_id": StatusUserEnum.ACTIVE
    }
    return count_rows(session=session, model = User, filter_conditions=filters)

@router.get("/me", response_model=UserRead)
def me(session: SessionDep,current_user: User = Depends(get_current_user)):
    if(_check_user_is_active(current_user)):
        return session.get(User, current_user.id, options=[joinedload(User.user_info)]) # type: ignore
            
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@router.patch("/me", response_model=UserRead)
def update_me(
    session: SessionDep, 
    current_user: User = Depends(get_current_user), 
    user_data: UserPatch = Body(...)
):
    if(_check_user_is_active(current_user)):
        assert current_user.id is not None
        return user_service.patch_self(user_id=current_user.id, session=session, user_data=user_data)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
 
@router.delete("/me")
def delete_me(session: SessionDep, current_user: User = Depends(get_current_user)):
    if(_check_user_is_active(current_user)):
        assert current_user.id is not None
        return user_service.delete_self(user_id=current_user.id, session=session)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or already deleted")


@router.patch("/{user_id}/role", 
        responses={
            status.HTTP_404_NOT_FOUND: {"description": "User not found"}
        })
def patch_user(
    user_id: int,
    session: SessionDep,
    role_id: RoleEnum,
    current_user: User = require_role(RoleEnum.ADMIN)
    ):
    try:
        user_service.patch_user(user_id=user_id, session=session, role_id=role_id)
        return {"message": "User role updated successfully"}
    except UserNotFoundException as e:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail=str(e))
    
@router.delete("/{user_id}")
def delete_user(user_id: int, session: SessionDep, current_user: User = require_role(RoleEnum.ADMIN)):  
    if(_check_user_is_active): 
        return user_service.delete_user_by_admin(user_id=user_id, session=session)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or already deleted")

@router.get("/{user_id}", responses={
        status.HTTP_404_NOT_FOUND: {"description": "User not found"}
    })
def get_user_by_id(user_id: int, session: SessionDep, current_user: User = Depends(get_current_user)):
    try:
        return user_service.get_user_by_id(user_id=user_id, session=session)
    except UserNotFoundException as e:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail=str(e))


