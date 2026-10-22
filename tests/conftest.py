import os
from collections.abc import AsyncGenerator

# for shared fixtures [All tests]
# Autodetected by Pytest

os.environ["DATABASE_URL"] = "postgresql+psycopg://bloguser:blogpass@localhost/test_blog"  # TEST CREDENTIALS

os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

# WHY WE HAVE 2 SAME KEY - BOTO USES AWS_* credentials so to mock the cred we use both
os.environ["S3_ACCESS_KEY_ID"] = "testing"
os.environ["S3_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_BUCKET_REGION"] = "us-east-1"

os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_BUCKET_REGION"] = "us-east-1"
# IMPORT IS VERY IMPORTANT ENV SHALL IMPORTED FIRST SO THAT THE ORIGINAL ENV ARE NOT LOADED

import boto3
import pytest
from httpx import ASGITransport, AsyncClient  # Async Test Req are done with these
from moto import mock_aws
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from database import Base, get_db
from main import app

pytest_plugins = ["anyio"]  # loads the AnyIO pytest plugin, which adds support for testing asynchronous code that uses AnyIO, asyncio, or trio.

import asyncio
import sys


# Fixture that returns which backend to be used out of these[async,trio,AnyIO]
@pytest.fixture(scope="session")    #Scope = once for entire test session than running once/test case
def anyio_backend():    # session - one event loop is created for the whole tests
    return "asyncio"    # if this was fun then for each fun there would be seperate event loop

# We use rollback method for db - first create and then rollback all transactions

@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(
        os.environ["DATABASE_URL"],
        poolclass=NullPool
    )
    return engine

@pytest.fixture(scope="session")
async def setup_database(test_engine):    # Create all the tables and then drop all other tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()

# TRANSACTIONAL ROLLBACK PATTERN
@pytest.fixture()   # Scope here is function so run for each fun
async def db_session(test_engine, setup_database) -> AsyncGenerator[AsyncSession]:
    conn = await test_engine.connect()
    tras = await conn.begin()

    test_async_session = async_sessionmaker(
        bind=conn,
        class_= AsyncSession,
        expire_on_commit= False,
        join_transaction_mode = "create_savepoint"  # Fake commit - stead of real commit it creates savepoint
    )

    async with test_async_session() as session:
        try:
            yield session
        finally:
            await session.close()
            await tras.rollback()
            await conn.close()

# MOTO fixture - AWS MOCK
@pytest.fixture()
def mocked_aws():
    with mock_aws():
        s3 = boto3.client("s3", region_name="eu-north-1")
        s3.create_bucket(Bucket=os.environ["S3_BUCKET_NAME"])
        yield s3

# Dependancy override 
@pytest.fixture
async def client(
    db_session: AsyncSession,
    mocked_aws
)-> AsyncGenerator[AsyncClient]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db  # Dependancy Injection

    async with AsyncClient(
        transport=ASGITransport(app=app),   # ASGI - Async Server Gateway Interphase - standard which define how async server like uvicorn talk to async py
        base_url="http://test"  # Basically this removes all the nw call and everything happens in memory [No HTTP server involved]
    ) as ac:
        yield ac

    app.dependency_overrides.clear()    # Checkout lifespan fun for this ASGI so that we can setup cache and other things

async def create_test_user(
        client: AsyncClient,
        username: str = "test",
        email: str = "testemail@mail.com",
        password:str = "testpassword"
) -> dict:
    response = await client.post(
        "/api/users",
        json={
            "username":username,
            "email":email,
            "password" : password,
        }   # We use JSON here cause of the input model
    )
    assert response.status_code == 201, f"Failed to create user: {response.text}"   # 2nd is optional op [,]
    return response.json()

async def login_user(
        client= AsyncClient,
        email:str = "test@example.com",
        password:str = "testpassword123"
) -> str:
    response = await client.post(
        "/api/users/token",
        data={
            "username":email,
            "password":password
        },  # using data cause in the api we expect form_data 
    )

    assert response.status_code == 200, f"Failed to login {response.text}"
    return response.json()["access_token"]

async def auth_header(token:str)->dict[str,str]:
    return {"Authorization":f"Bearer {token}"}