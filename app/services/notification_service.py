from sqlalchemy.orm import Session
from uuid import UUID
from app.core.ws_manager import manager


async def send_notification(
    user_id: str,
    title: str,
    body: str,
    notification_type: str,
    data: dict,
    db: Session,
):
    """
    Central notification function:
    1. Persist notification in the database
    2. Push via WebSocket (real-time)
    3. Extensible for FCM / WhatsApp later
    """

    if isinstance(user_id, str):
        # Explicit UUID cast prevents SQLAlchemy CompileError (f405) in Postgres inserts
        try:
            parsed_user_id = UUID(user_id)
        except ValueError:
            parsed_user_id = user_id
    else:
        parsed_user_id = user_id

    # 1. Persist to DB
    from app.models.notification import Notification
    notification = Notification(
        user_id=parsed_user_id,
        title=title,
        body=body,
        type=notification_type,
        data=data,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # 2. Push via WebSocket (real-time in-app)
    ws_payload = {
        "type": notification_type,
        "notification_id": str(notification.id),
        "title": title,
        "body": body,
        **data,
    }
    
    if manager.is_connected(user_id):
        await manager.send_to_user(user_id, ws_payload)
    else:
        # 3. FCM Fallback (Stubbed for now)
        # We need the user's fcm_token from the database to send the push
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.fcm_token:
            print(f"[FCM STUB] Sending push to {user.full_name} (Token: {user.fcm_token})")
            print(f"           Title: {title} | Body: {body}")
            # TODO: import firebase_admin and send native push using FCM SDK
        else:
            print(f"[FCM STUB] User {user_id} is offline and has no FCM token registered.")

    return notification
