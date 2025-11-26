from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import Session, text
from dependencies.auth_dependencies import oauth2_scheme
from fastapi.middleware.cors import CORSMiddleware
from controllers import auth_controller, post_controller, report_controller, users_controller, chats_controller
from core import database
from models.seed import admingen
from core.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # database.create_db_and_tables()
    # with Session(engine) as session:
    
    #     seed_data(session)

    try:
        with Session(engine) as session:
            # Verifica que la conexión funciona
            session.exec(text("SELECT 1")) # type: ignore
            print("✅ Conexión a base de datos exitosa.")
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        raise e

    yield
    # Shutdown: runs when the app shuts down (optional cleanup)
    # e.g., close database connections, etc.

app = FastAPI(lifespan=lifespan)

#CORS
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_controller.router)
app.include_router(users_controller.router)
app.include_router(post_controller.router)
app.include_router(report_controller.router)
app.include_router(chats_controller.router)
