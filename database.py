from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blob.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

AsyncSessionLocal =async_sessionmaker(
    engine,
    class_= AsyncSession,
    expire_on_commit= False
    )
# This base classes is inherited by other classes and based on that orm and table are refrenced
class Base(DeclarativeBase):    # DeclarativeBase - lets SQLAlchemy map Python classes to database tables.
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        


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