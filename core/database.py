import os
from typing import Annotated
from dotenv import load_dotenv
from fastapi import Depends
from sqlmodel import SQLModel, create_engine, Session
from models import *
from core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=True)  # echo=True solo para debug

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
