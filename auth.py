from datetime import datetime, timedelta, UTC
import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from config import settings


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

    encode_jwt = jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm
    )
    return encode_jwt


def verify_access_token(access_token: str) -> str | None:
    '''Verify JWT access token and return the subject (user_id) if valid '''
    print(settings.secret_key.get_secret_value())
    print(settings.algorithm)
    print(access_token)
    try:
        payload = jwt.decode(
            access_token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={'require': ['exp', 'sub']}
        )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")   # returning this cause we will store the userid in the sub field


# JWT => Header[Algo & Type] + Payload[Data & Expiration] + Signature[Proves the token is not tampered] [Created with our secret key]
