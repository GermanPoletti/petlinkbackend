from sqlmodel import select, Session
from models import City, StateProvince, PostType, Role, StatusUser, StatusAgreement

MAPPINGS = {
    "post_type": PostType,
    "role": Role,
    "status_user": StatusUser,
    "agreement_status": StatusAgreement
}

class MapperError(ValueError):
    pass

def get_id_by_name(session: Session, model, name: str) -> int:
    row = session.exec(
        select(model).where(model.name == name)
    ).first()
    if not row:
        raise MapperError(f"{model.__name__}: '{name}' no existe")
    return row.id

def get_city_id_by_name_and_province(session: Session, city_name: str, province_name: str) -> int:
    province = session.exec(
        select(StateProvince).where(StateProvince.name == province_name)
    ).first()
    if not province:
        raise MapperError(f"Provincia '{province_name}' no existe")

    city = session.exec(
        select(City).where(City.name == city_name, City.state_province_id == province.id)
    ).first()
    if not city:
        raise MapperError(f"Ciudad '{city_name}' no existe en la provincia '{province_name}'")

    return city.id # type: ignore

def map_names_to_ids(session: Session, data: dict) -> dict:
    mapped = {}
    for field, value in data.items():
        if field in MAPPINGS:
            model = MAPPINGS[field]
            mapped[f"{field}_id"] = get_id_by_name(session, model, value)
        elif field == "city":
            province_name = data.get("province")
            if not province_name:
                raise MapperError("Se debe indicar la provincia cuando se indica la ciudad")
            mapped["city_id"] = get_city_id_by_name_and_province(session, value, province_name)
        else:
            mapped[field] = value
    return mapped

def map_ids_to_names(obj, fields: dict) -> dict:
    result = {}
    for attr, model in fields.items():
        related_obj = getattr(obj, attr)
        result[attr] = related_obj.name if related_obj else None
    return result
