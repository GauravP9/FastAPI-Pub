from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./blob.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush= False, bind= engine)

# This base classes is inherited by other classes and based on that orm and table are refrenced
class Base(DeclarativeBase):    # DeclarativeBase - lets SQLAlchemy map Python classes to database tables.
    pass

def get_db():
    with SessionLocal() as db:
        yield db


# FLOW
# create_engine()
# ↓
# Engine
# ↓
# SessionLocal
# ↓
# DB Session
# ↓
# Query