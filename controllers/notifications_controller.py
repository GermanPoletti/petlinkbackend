from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlmodel import select, delete

from core.database import SessionDep
from dependencies.auth_dependencies import get_current_user
from models.user.user import User
from models.notification.push_token import UserPushToken
from models.notification.subscription import NotificationSubscription
from schemas.notification_schemas import TokenRegister, SubscriptionUpdate, SubscriptionRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.put("/token", summary="Register or update the user's Expo push token")
def register_push_token(
    body: TokenRegister,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    existing = session.get(UserPushToken, current_user.id)
    if existing:
        existing.token = body.token
        existing.latitude = body.latitude
        existing.longitude = body.longitude
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
    else:
        session.add(UserPushToken(
            user_id=current_user.id,
            token=body.token,
            latitude=body.latitude,
            longitude=body.longitude,
            updated_at=datetime.now(timezone.utc),
        ))
    session.commit()
    return {"detail": "Token registrado"}


@router.delete("/token", summary="Remove the user's push token (called on logout)")
def delete_push_token(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    existing = session.get(UserPushToken, current_user.id)
    if existing:
        session.delete(existing)
        session.commit()
    return {"detail": "Token eliminado"}


@router.get("/subscriptions", response_model=list[SubscriptionRead])
def get_subscriptions(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    return session.exec(
        select(NotificationSubscription).where(
            NotificationSubscription.user_id == current_user.id
        )
    ).all()


@router.put("/subscriptions", summary="Replace all notification subscriptions for the user")
def update_subscriptions(
    body: SubscriptionUpdate,
    session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    session.exec(  # type: ignore
        delete(NotificationSubscription).where(
            NotificationSubscription.user_id == current_user.id
        )
    )
    for sub in body.subscriptions:
        session.add(NotificationSubscription(
            user_id=current_user.id,
            post_type_id=sub.post_type_id,
            category=sub.category,
        ))
    session.commit()
    return {"detail": f"{len(body.subscriptions)} suscripciones guardadas"}
