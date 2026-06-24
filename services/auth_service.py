import uuid
import jwt
from pwdlib import PasswordHash
from fastapi import HTTPException, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone

from exceptions import SessionAlreadyClosed
from models import TokensBlacklist, User, ActiveToken, EmailVerificationToken
from core.config import settings
from schemas.auth_schemas import *
from schemas.user_schemas import UserCreate


password_hash = PasswordHash.recommended()

#Use this when you have the token to invalidate (example: user self-logout)
def invalidate_token(session: Session, token: str) -> TokensBlacklist:
    decoded_token = decode_token(token)

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

#Use this when you dont have the token to invalidate (example: user deleted by admin)
def terminate_active_session(session: Session, user_id: int):
    active_session = session.exec(select(ActiveToken).where(ActiveToken.user_id == user_id)).first()

    if not active_session:
        return False

    token_for_blacklist = TokensBlacklist(
        jti=active_session.jti,
        user_id=active_session.user_id,
        expires_at=active_session.expires_at
    )

    session.add(token_for_blacklist)
    session.delete(active_session)
    session.commit()

    return True

def _add_active_session(session: Session, user_id: int, jti, expires_at):
    session.add(ActiveToken(user_id=user_id, jti=jti, expires_at=expires_at))
    session.commit()

def encrypt_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


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
    _add_active_session(session, user_id=data["user_id"], jti=to_encode["jti"], expires_at=expire)

    return encoded_jwt

def decode_token(token: str):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

def register_user(user_data: UserCreate, session: Session) -> tuple[User, str]:
    user_already_exists = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()

    if user_already_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    new_user = User(
        email=user_data.email,
        password_hash=encrypt_password(user_data.password),
        email_verified=False,
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    token_str = _create_verification_token(new_user.id, session)  # type: ignore
    return new_user, token_str

def _create_verification_token(user_id: int, session: Session) -> str:
    # Invalidate any previous unused tokens for this user
    old_tokens = session.exec(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used == False,  # noqa: E712
        )
    ).all()
    for t in old_tokens:
        session.delete(t)

    token_str = uuid.uuid4().hex
    ev_token = EmailVerificationToken(
        user_id=user_id,
        token=token_str,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    session.add(ev_token)
    session.commit()
    return token_str

def verify_email(token: str, session: Session) -> str:
    ev_token = session.exec(
        select(EmailVerificationToken).where(EmailVerificationToken.token == token)
    ).first()

    if not ev_token or ev_token.used:
        return _html_response("error", "El link ya fue utilizado o no es válido. Solicitá uno nuevo desde la app.")

    now = datetime.now(timezone.utc)
    token_tz = ev_token.expires_at.replace(tzinfo=timezone.utc) if ev_token.expires_at.tzinfo is None else ev_token.expires_at
    if now > token_tz:
        return _html_response("error", "El link expiró. Solicitá uno nuevo desde la app.")

    user = session.get(User, ev_token.user_id)
    if not user:
        return _html_response("error", "Usuario no encontrado.")

    user.email_verified = True
    ev_token.used = True
    session.add(user)
    session.add(ev_token)
    session.commit()

    return _html_response("success", "¡Email verificado con éxito! Volvé a la app y tocá <strong>Ya verifiqué</strong>.")

def resend_verification(user: User, session: Session) -> str:
    if user.email_verified:
        raise HTTPException(status_code=400, detail="El email ya está verificado")

    token_str = _create_verification_token(user.id, session)  # type: ignore
    return token_str

def get_verification_status(user: User, session: Session) -> dict:
    fresh = session.get(User, user.id)
    return {"email_verified": fresh.email_verified if fresh else False}

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

    # Check if user is banned
    if user.banned_until:
        ban_tz = user.banned_until.replace(tzinfo=timezone.utc) if user.banned_until.tzinfo is None else user.banned_until
        if datetime.now(timezone.utc) < ban_tz:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tu cuenta está suspendida hasta {ban_tz.strftime('%d/%m/%Y %H:%M')} UTC",
            )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(
        session=session,
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": user.role.name,
            "email_verified": user.email_verified,
        },
        expires_delta=access_token_expires
    )
    expires_at = datetime.now(timezone.utc) + access_token_expires

    return Token(access_token=access_token, user_id=user.id, expires_at=int(expires_at.timestamp() * 1000))

def logout(token: str, session: Session):
    disabled_token = invalidate_token(session=session, token=token)
    session.refresh(disabled_token)
    return {"detail": "logout succesful"}


def _html_response(result_type: str, message: str) -> str:
    color = "#2E7D32" if result_type == "success" else "#C62828"
    icon = "✅" if result_type == "success" else "❌"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Petlink — Verificación</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f5f5f5; display: flex;
           justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
    .card {{ background: white; border-radius: 16px; padding: 40px 36px; max-width: 440px;
             width: 90%; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.1); }}
    h2 {{ color: {color}; }}
    p {{ color: #444; font-size: 16px; line-height: 1.5; }}
    .icon {{ font-size: 52px; margin-bottom: 12px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h2>Petlink</h2>
    <p>{message}</p>
  </div>
</body>
</html>"""
