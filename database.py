from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import settings


engine = create_async_engine(
    settings.database_url,
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