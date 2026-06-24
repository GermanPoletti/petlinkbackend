from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from core.config import settings
from exceptions import SessionAlreadyClosed
from models.enums import RoleEnum
from models.user.user import User
from services import auth_service, email_service
from core.database import SessionDep
from schemas.auth_schemas import LoginData
from schemas.user_schemas import *
from dependencies.auth_dependencies import get_current_user, oauth2_scheme

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    data = LoginData(email=form_data.username, password=form_data.password)
    return auth_service.login(data, session)


@router.get("/is_admin")
def is_admin(current_user: User = Depends(get_current_user)):
    return {"is_admin": True if current_user.role_id == RoleEnum.ADMIN else False}


@router.post("/logout", description="Logs out a user & blacklist his token & and his session")
def logout(session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        return auth_service.logout(token, session)
    except SessionAlreadyClosed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already loggued out")


@router.post("/register", response_model=UserRead)
def register(user_data: UserCreate, session: SessionDep, background_tasks: BackgroundTasks):
    user, token_str = auth_service.register_user(user_data, session)
    link = f"{settings.BASE_URL}/auth/verify?token={token_str}"
    background_tasks.add_task(email_service.send_verification_email, user.email, link)
    return user


@router.get("/verify", response_class=HTMLResponse)
def verify_email(token: str, session: SessionDep):
    html = auth_service.verify_email(token, session)
    return HTMLResponse(content=html)


@router.post("/resend-verification")
def resend_verification(
    session: SessionDep,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    token_str = auth_service.resend_verification(current_user, session)
    link = f"{settings.BASE_URL}/auth/verify?token={token_str}"
    background_tasks.add_task(email_service.send_verification_email, current_user.email, link)
    return {"detail": "Email de verificación enviado"}


@router.get("/verification-status")
def verification_status(session: SessionDep, current_user: User = Depends(get_current_user)):
    return auth_service.get_verification_status(current_user, session)


def refresh_token():
    pass
