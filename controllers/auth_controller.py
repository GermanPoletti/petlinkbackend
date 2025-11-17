from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from exceptions import SessionAlreadyClosed
from services import auth_service
from core.database import SessionDep
from schemas.auth_schemas import LoginData
from schemas.user_schemas import *
from dependencies.auth_dependencies import oauth2_scheme

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    data = LoginData(email=form_data.username, password=form_data.password)
    return auth_service.login(data, session)



@router.post("/logout", description= "Logs out a user & blacklist his token & and his session")
def logout(session: SessionDep, token: Annotated[str, Depends(oauth2_scheme)]):
    print(token)
    try:    
        return auth_service.logout(token, session) 
    except(SessionAlreadyClosed):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already loggued out")
    
@router.post("/register", response_model=UserRead)
def register(user_data: UserCreate, session: SessionDep):
    return auth_service.register_user(user_data, session)

def refresh_token():
    pass