import uuid
import jwt
from pwdlib import PasswordHash
from fastapi import HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone

from exceptions import SessionAlreadyClosed
from models import TokensBlacklist, User, ActiveToken
from core.config import settings
from schemas.auth_schemas import *
from schemas.user_schemas import UserCreate


password_hash = PasswordHash.recommended()

#Use this when you have the token to invalidate (example: user self-logout)
def invalidate_token(session: Session, token: str) -> TokensBlacklist:
    decoded_token = decode_token(token)

    #TODO: raise custom exception when token is already blacklisted

    if session.exec(select(TokensBlacklist).where(TokensBlacklist.jti == decoded_token["jti"])).first():
        raise SessionAlreadyClosed("The session you want to close is alredy closed")

    disabled_token = TokensBlacklist(
        jti=decoded_token["jti"],
        user_id=decoded_token["user_id"],
        expires_at=datetime.fromtimestamp(decoded_token["exp"], tz=timezone.utc)
    )
    

    active_session = session.exec(
        select(ActiveToken).where(ActiveToken.jti == decoded_token["jti"])
    ).first()

    if active_session:
        session.delete(active_session)

    session.add(disabled_token)
    session.commit()
    return disabled_token

#Use this when you dont have the token to to invalidate (example: user deleted by admin)
def terminate_active_session(session: Session, user_id: int):
    active_session = session.exec(select(ActiveToken).where(ActiveToken.user_id == user_id)).first()
    
    if not active_session:
        return False
    
    token_for_blacklist = TokensBlacklist(
        jti = active_session.jti,
        user_id = active_session.user_id,
        expires_at=active_session.expires_at
    )
    
    session.add(token_for_blacklist)
    session.delete(active_session)
    session.commit

    return True

def _add_active_session(session: Session, user_id: int, jti, expires_at):
    session.add(ActiveToken(user_id= user_id, jti = jti, expires_at = expires_at))
    session.commit()

def encrypt_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


#Funciones referenciadas desde endpoints:

def create_token(session: Session, data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({
        "exp": expire, 
        "jti": str(uuid.uuid4())
        })

    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    _add_active_session(session, user_id = data["user_id"], jti= to_encode["jti"], expires_at=expire)

    return encoded_jwt

def decode_token(token: str):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def register_user(user_data: UserCreate, session: Session) -> User:
    new_user = User(
        username = user_data.username,
        first_name = user_data.first_name,
        last_name = user_data.last_name,
        email = user_data.email,
        password_hash = encrypt_password(user_data.password),
        photo_url = user_data.photo_url
        )
    
    user_already_exists = session.exec(
        select(User).where((User.username == new_user.username) | (User.email == new_user.email))
    ).first()
    
    if user_already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return new_user

def login(form_data: LoginData, session: Session) -> Token:


    user: User | None = session.exec(
        select(User).where(User.email == form_data.email)
    ).first()


    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    assert user.id is not None
    active_session = terminate_active_session(session, user.id)

    if active_session:
        print("\n\n -----------Prior session closed----------- \n\n")

    if user.status_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not active",
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(
        session= session,
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )


    return Token(access_token=access_token)
      
def logout(token: str, session: Session):
    
    disabled_token = invalidate_token(session = session, token = token)

    session.refresh(disabled_token)

    return {"detail": "logout succesful"}
