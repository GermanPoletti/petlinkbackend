from pydantic import BaseModel


class ReportBase(BaseModel):
    post_id: int 
    reason: str 

class ReportCreate(ReportBase):
    model_config = {
        "from_attributes": True
    }
    

class ReportRead(ReportBase):
    id: int
    reporting_user_id: int
    is_reviewed: bool

    model_config = {
        "from_attributes": True
    }