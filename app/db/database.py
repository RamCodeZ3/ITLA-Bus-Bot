from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from db.models import Base

DATABASE_URL = "sqlite:///itla_bot.db"

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
