from sqlmodel import Field, Column, DATETIME, func
from datetime import datetime
from typing import Optional
from datetime import datetime, timezone

class TimestampMixin:
    created_at: datetime = Field(default_factory= lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: None,
        sa_column_kwargs={"onupdate": func.current_timestamp()},
    )
