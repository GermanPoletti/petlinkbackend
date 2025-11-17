# seeds/populate_argentina.py
# type: ignore


import requests
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from models import Country, StateProvince, City
from core.database import engine  # ← AJUSTA LA RUTA

def populate_argentina():
    with Session(engine) as session:
        base_url = "https://apis.datos.gob.ar/georef/api/v2.0"
        
        # === 1. País: Argentina ===
        argentina = Country(name="Argentina", code="AR")
        try:
            session.add(argentina)
            session.commit()
            session.refresh(argentina)
            country_id = argentina.id
            print(f"País creado: {argentina.name} (ID: {country_id})")
        except IntegrityError:
            session.rollback()
            existing = session.exec(select(Country).where(Country.code == "AR")).first()
            country_id = existing.id
            print(f"País ya existe: {existing.name} (ID: {country_id})")

        # === 2. Provincias ===
        resp = requests.get(
            f"{base_url}/provincias",
            params={"campos": "id,nombre", "orden": "nombre", "formato": "json"}
        )
        resp.raise_for_status()
        provincias = resp.json()["provincias"]

        for prov in provincias:
            sp = StateProvince(country_id=country_id, name=prov["nombre"])
            try:
                session.add(sp)
                session.commit()
                session.refresh(sp)
                prov_id = sp.id
                print(f"  Provincia: {prov['nombre']} (ID: {prov_id})")
            except IntegrityError:
                session.rollback()
                existing = session.exec(
                    select(StateProvince).where(
                        StateProvince.name == prov["nombre"],
                        StateProvince.country_id == country_id
                    )
                ).first()
                prov_id = existing.id
                print(f"  Provincia ya existe: {prov['nombre']} (ID: {prov_id})")

            # === 3. Localidades (Ciudades) ===
            offset = 0
            while True:
                loc_resp = requests.get(
                    f"{base_url}/localidades",
                    params={
                        "provincia": prov["id"],
                        "campos": "nombre",
                        "orden": "nombre",
                        "max": 1000,
                        "inicio": offset,
                        "formato": "json"
                    }
                )
                loc_resp.raise_for_status()
                data = loc_resp.json()
                localidades = data.get("localidades", [])
                total = data.get("total", 0)

                if not localidades:
                    break

                for loc in localidades:
                    city = City(name=loc["nombre"], state_province_id=prov_id)
                    try:
                        session.add(city)
                        session.commit()
                    except IntegrityError:
                        session.rollback()
                        # Ya existe → ignorar
                        pass

                offset += 1000
                if offset >= total:
                    break

        print("¡Población completada! Ciudades, provincias y país insertados.")

# Ejecutar solo si se llama directamente
if __name__ == "__main__":
    populate_argentina()