from __future__ import annotations
import math
import logging
import httpx

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_EXPO_HEADERS = {
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Content-Type": "application/json",
}


def _is_valid_expo_token(token: str) -> bool:
    return token.startswith("ExponentPushToken[") or token.startswith("ExpoPushToken[")


def _send_raw(messages: list[dict]) -> None:
    """POST up to 100 messages to the Expo Push API in a single request."""
    try:
        httpx.post(
            EXPO_PUSH_URL,
            json=messages if len(messages) > 1 else messages[0],
            headers=_EXPO_HEADERS,
            timeout=10.0,
        ).raise_for_status()
    except Exception as exc:
        logger.error("Expo push request failed: %s", exc)


def send_push(
    token: str,
    title: str,
    body: str,
    data: dict | None = None,
) -> None:
    if not _is_valid_expo_token(token):
        logger.warning("Skipping invalid Expo push token: %.40s", token)
        return
    _send_raw([{"to": token, "title": title, "body": body, "sound": "default", "data": data or {}}])


def send_push_bulk(tokens: list[str], title: str, body: str, data: dict | None = None) -> None:
    valid = [t for t in tokens if _is_valid_expo_token(t)]
    if not valid:
        return
    messages = [
        {"to": t, "title": title, "body": body, "sound": "default", "data": data or {}}
        for t in valid
    ]
    for i in range(0, len(messages), 100):
        _send_raw(messages[i : i + 100])


# ---------------------------------------------------------------------------
# Background task helpers — each opens its own DB session so they can run
# safely after the HTTP response has already been sent.
# ---------------------------------------------------------------------------

def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def notify_chat_recipient(
    chat_id: int,
    sender_id: int,
    message_preview: str,
) -> None:
    """Send a push notification to the other participant of a chat."""
    from core.database import engine
    from sqlmodel import Session
    from models.chat.chat import Chat
    from models.notification.push_token import UserPushToken
    from models.user.user import User, UserProfiles

    with Session(engine) as session:
        chat = session.get(Chat, chat_id)
        if not chat or not chat.is_active:
            return

        recipient_id = chat.receiver_id if chat.initiator_id == sender_id else chat.initiator_id
        token_row = session.get(UserPushToken, recipient_id)
        if not token_row:
            print("no hay token")
            return
        sender_profile = session.get(UserProfiles, sender_id)
        sender_name = getattr(sender_profile, "username", None)
        if not sender_name:
            sender = session.get(User, sender_id)
            sender_name = getattr(sender, "email", "Usuario").split("@")[0]

        send_push(
            token=token_row.token,
            title=sender_name,
            body=message_preview[:100],
            data={"type": "chat_message", "chat_id": chat_id},
        )


def notify_post_subscribers(
    post_id: int,
    post_type_id: int,
    category: str,
    post_author_id: int,
    post_title: str,
    post_lat: float | None,
    post_lon: float | None,
    radius_m: float = 50_000.0,
) -> None:
    """
    Send push notifications to users subscribed to (post_type_id, category)
    who are within radius_m metres of the new post (based on their registered
    location in user_push_tokens). Users with no stored location are notified
    regardless of distance.
    """
    from core.database import engine
    from sqlmodel import Session, select
    from models.notification.subscription import NotificationSubscription
    from models.notification.push_token import UserPushToken

    with Session(engine) as session:
        subscriber_ids = session.exec(
            select(NotificationSubscription.user_id).where(
                NotificationSubscription.post_type_id == post_type_id,
                NotificationSubscription.category == category,
                NotificationSubscription.user_id != post_author_id,
            )
        ).all()

        if not subscriber_ids:
            return

        token_rows: list[UserPushToken] = session.exec(
            select(UserPushToken).where(UserPushToken.user_id.in_(subscriber_ids))  # type: ignore
        ).all()

        tokens: list[str] = []
        for row in token_rows:
            if (
                post_lat is None
                or post_lon is None
                or row.latitude is None
                or row.longitude is None
                or _haversine_m(post_lat, post_lon, row.latitude, row.longitude) <= radius_m
            ):
                tokens.append(row.token)

        if not tokens:
            return

        type_label = "Oferta" if post_type_id == 1 else "Necesidad"
        send_push_bulk(
            tokens=tokens,
            title=f"Nueva {type_label} de {category}",
            body=post_title,
            data={"type": "new_post", "post_id": post_id, "post_type_id": post_type_id},
        )
