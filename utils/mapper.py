from sqlmodel import select, Session
from sqlalchemy import func
from models import PostType, Role, StatusUser, StatusAgreement

MAPPINGS = {
    "oferta": PostType,
    "necesidad": PostType,
    "role": Role,
    "status_user": StatusUser,
    "agreement_status": StatusAgreement,
}


class MapperError(ValueError):
    pass


def _normalize(value: str) -> str:
    return value.strip().lower()


def get_id_by_name(session: Session, model, name: str) -> int:
    normalized = _normalize(name)
    row = session.exec(
        select(model).where(func.lower(model.name) == normalized)
    ).first()
    if not row:
        raise MapperError(f"{model.__name__}: '{name}' no existe")
    return row.id


def map_names_to_ids(session: Session, data: dict) -> dict:
    mapped = {}
    for field, value in data.items():
        if field in MAPPINGS:
            model = MAPPINGS[field]
            mapped[f"{field}_id"] = get_id_by_name(session, model, value)
        else:
            mapped[field] = value
    return mapped


def map_ids_to_names(obj, fields: dict) -> dict:
    result = {}
    for attr, model in fields.items():
        related_obj = getattr(obj, attr)
        if related_obj is None:
            result[attr] = None
        else:
            if not hasattr(related_obj, "name"):
                raise MapperError(f"{model.__name__} no tiene atributo 'name'")
            result[attr] = related_obj.name
    return result
