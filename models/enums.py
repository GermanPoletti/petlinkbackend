from enum import IntEnum

class RoleEnum(IntEnum):
    USER = 1
    MODERATOR = 2
    ADMIN = 3

class StatusUserEnum(IntEnum):
    ACTIVE = 1
    DELETED = 2
    BANNED = 3

class PostTypeEnum(IntEnum):
    OFERTA = 1
    PROPUESTAS = 2

class AgreementStatusEnum(IntEnum):
    PENDING = 1
    REJECTED = 2
    COMPLETED = 3
