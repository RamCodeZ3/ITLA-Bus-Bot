import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .models import Base


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(CURRENT_DIR, "..", "data")
DB_NAME = "itla_bot.db"

if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

db_path = os.path.abspath(os.path.join(DB_FOLDER, DB_NAME))
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


# SQLite ignora foreign keys por defecto — esto las activa
@event.listens_for(engine, "connect")
def set_sqlite_pragma(conn, _):
    conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()