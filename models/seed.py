from sqlmodel import Session, select

from services import auth_service
from .core.role import Role
from .core.status_user import StatusUser
from .core.post_type import PostType
from .core.status_agreement import StatusAgreement
from .user.user import User
from .enums import RoleEnum, StatusUserEnum, PostTypeEnum, AgreementStatusEnum
from datetime import datetime

def seed_data(session: Session):
    roles = [
        Role(id=RoleEnum.USER, name="user"),
        Role(id=RoleEnum.MODERATOR, name="moderator"),
        Role(id=RoleEnum.ADMIN, name="admin"),
    ]
    for r in roles:
        if not session.get(Role, r.id):
            session.add(r)

    statuses = [
        StatusUser(id=StatusUserEnum.ACTIVE, name="active"),
        StatusUser(id=StatusUserEnum.DELETED, name="deleted"),
        StatusUser(id=StatusUserEnum.BANNED, name="banned"),
    ]
    for s in statuses:
        if not session.get(StatusUser, s.id):
            session.add(s)

    post_types = [
        PostType(id=PostTypeEnum.OFERTA, name="Oferta"),
        PostType(id=PostTypeEnum.NECESIDAD, name="Necesidad"),
    ]
    for pt in post_types:
        if not session.get(PostType, pt.id):
            session.add(pt)

    agreement_statuses = [
        StatusAgreement(id=AgreementStatusEnum.PENDING, name="pending"),
        StatusAgreement(id=AgreementStatusEnum.REJECTED, name="rejected"),
        StatusAgreement(id=AgreementStatusEnum.COMPLETED, name="completed"),
    ]
    for sa in agreement_statuses:
        if not session.get(StatusAgreement, sa.id):
            session.add(sa)


def admingen(session: Session):
    if not session.exec(select(User).where(User.email == "petlinkproject@gmail.com")).first():
        admin = User(
            username="admin",
            first_name="Admin",
            last_name="PetLink",
            email="petlinkproject@gmail.com",
            password_hash=auth_service.encrypt_password("petlinkadmin123"),
            role_id=RoleEnum.ADMIN,
            status_id=StatusUserEnum.ACTIVE,
        )
        session.add(admin)

    session.commit()