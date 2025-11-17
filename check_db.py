# check_models.py
import logging
from sqlmodel import SQLModel, Session
from sqlalchemy import inspect
from core.database import engine
from models import __all__ as model_names
import models

# 🔇 Silenciar logs de SQLAlchemy
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

def check_models():
    print("🔍 Cargando modelos...")
    model_classes = [getattr(models, name) for name in model_names]
    print(f"✅ {len(model_classes)} modelos importados correctamente.\n")

    with Session(engine) as session:
        inspector = inspect(engine)
        for model in model_classes:
            table_name = model.__tablename__
            print(f"🧩 Tabla: {table_name}")

            # Columnas del modelo
            model_cols = set(model.__table__.columns.keys())
            # Columnas de la base de datos
            if inspector.has_table(table_name):
                db_cols = set([col["name"] for col in inspector.get_columns(table_name)])
            else:
                print(f"❌ La tabla '{table_name}' no existe en la base de datos.")
                continue

            missing_in_db = model_cols - db_cols
            extra_in_db = db_cols - model_cols

            if missing_in_db:
                print(f"⚠️ Faltan en BD: {missing_in_db}")
            if extra_in_db:
                print(f"⚠️ Sobran en BD: {extra_in_db}")
            if not missing_in_db and not extra_in_db:
                print("✅ Columnas coinciden.")

            # Verificar Foreign Keys
            fks = {fk.parent.name: f"{fk.column.table.name}['{fk.column.name}']" 
                   for fk in model.__table__.foreign_keys}
            if fks:
                print("\n🔗 Claves foráneas:")
                for col, ref in fks.items():
                    print(f"  ['{col}'] → {ref}")
            print()  # Espacio entre tablas

if __name__ == "__main__":
    check_models()
