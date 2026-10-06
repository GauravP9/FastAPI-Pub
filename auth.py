from datetime import datetime, timedelta, UTC
import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Base, get_db
from config import settings
import models

password_hash = PasswordHash.recommended()  # Gives recommended settings for hashing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/users/token')  # tokenURL has to MATCH the login endpoint
# oAuthBearer - extracts the token from the header when user req


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password=password, hash=hashed_password)    # Return TRUE

# ENCRYPTION are reversible but HASHES are not


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    '''Create a JWT token'''
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(tz=UTC) + expires_delta
    else:
        expire = datetime.now(tz=UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({'exp': expire})   # Here the exp important JWT expext that keyword only others wont work\

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_access_token(access_token: str) -> str | None:
    '''Verify JWT access token and return the subject (user_id) if valid '''
    try:
        payload = jwt.decode(
            access_token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]}
        )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")   # returning this cause we will store the userid in the sub field


# JWT => Header[Algo & Type] + Payload[Data & Expiration] + Signature[Proves the token is not tampered] [Created with our secret key]

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]) -> models.User:
    """Get Current User from the Bearer Token And return error if otherwise"""
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Invalid or expired token',
                            headers={'WWW-Authenticate': 'Bearer'}
                            )
    try:
        user_id_int: int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid or expired token',
            headers={'WWW-Authenticate': 'Bearer'}
        )
    result = await db.execute(Select(models.User).where(models.User.id == int(user_id_int)))

    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Invalid or expired token',
                            headers={'WWW-Authenticate': 'Bearer'}
                            )
    return user

current_user = Annotated[models.User, Depends(get_current_user)]  # Makes the route signature cleaner
