from sqlmodel import Session, select, func
from typing import Type, Any
from sqlalchemy.orm import selectinload

def count_rows(session: Session, model: Type[Any], filter_conditions: dict | None = None) -> int:
    statement = select(func.count(model.id))  

    # Aplicar filtros si existen
    if filter_conditions:
        for column, value in filter_conditions.items():
            statement = statement.where(getattr(model, column) == value)
        
    result = session.exec(statement)
    count = result.first()
    return count # type: ignore