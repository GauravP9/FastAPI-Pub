from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import Select, func  # func - for case-insensetive query[Any func called on this become sql func func.lower(col) => lower(col)]
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from schemas import PostResponse, UserCreate, UserPublic, UserPrivate, UserUpdate, Token
import models

from datetime import timedelta
from auth import hash_password, current_user, verify_password, create_access_token
from config import settings


router = APIRouter()


# we will add prefix in main.py so withing user.py will have empty string and at end it will add up and become /api/user
@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):   # Create session and gives us and cleans afterwards
    result = await db.execute(
        Select(models.User).where(func.lower(models.User.username) == user.username.lower()),
    )

    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This username already exists in the db"
                            )
    # EMAIL CHECKING
    email_result = await db.execute(
        Select(models.User).where(func.lower(models.User.email) == user.email.lower()),
    )

    existing_email = email_result.scalars().first()

    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This email already exists in the db"
                            )

    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password)
    )

    db.add(new_user)    # No AWAIT here cause this only appends to session list
    await db.commit()
    await db.refresh(new_user)    # reload the object from the db confirming commit

    return new_user


@router.post('/token', status_code=status.HTTP_200_OK, response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[AsyncSession, Depends(get_db)]):
    # Look up user by email
    # NOTE: OAuth2 uses "username" field but we treat it as email

    result = await db.execute(
        Select(models.User).where(func.lower(models.User.email) == form_data.username.lower())
    )

    user = result.scalars().first()

    # Verify user exist and password is correct

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password",
                            headers={'WWW-Authenticate': "Bearer"}
                            )
    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)

    access_token = create_access_token(
        data={'sub': str(user.id)},
        expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type='bearer')

# OAuth2PasswordRequestForm - is a predefined FastAPI class that captures the login form fields (username, password, etc.) from the incoming HTTP request.
# is simply the value typed into the login form's username field (which in your application is being used as the email).


@router.get("/me", response_model=UserPrivate)  # This route for frontend to know who is logged in
async def get_current_user(current_user: current_user):
    """Get the current authenticated user"""
    return current_user


@router.get('/{user_id}', status_code=status.HTTP_200_OK, response_model=UserPrivate)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically
    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )
    existing_userid = result.scalars().first()

    if existing_userid:
        return existing_userid
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")


@router.get('/{user_id}/posts', response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )

    existing_userid = result.scalars().first()
    if not existing_userid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")

    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))  # Required in API
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
    )

    all_posts = result.scalars().all()
    # if all_posts:
    return all_posts
    # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No post found by this userid")


@router.patch('/{user_id}',  status_code=status.HTTP_200_OK, response_model=UserPrivate)  # Used patch here so fun name is also partial
async def update_user_partial(user_id: int, user_update: UserUpdate, current_user: current_user, db: Annotated[AsyncSession, Depends(get_db)]):

    if user_id != current_user.id:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Not authorized to update the user"
                             )

    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )   # Check if USER exists
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")

    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(
            Select(models.User).where(func.lower(models.User.username) == user_update.username.lower())  # Check if the new userid exists
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already present")

    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(
            Select(models.User).where(func.lower(models.User.email) == user_update.email.lower())
        )   # Check if the new email exists
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already present")

    update_data = user_update.model_dump(exclude_unset=True)  # NOTE: This make PATCH work, This helps only get the updated data from the req body

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email.lower()
    if user_update.username is not None:
        user.image_file = user_update.image_file

    await db.commit()  # How knows what to commit - Which objects have changed since they were loaded?
    await db.refresh(user)
    return user


@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)  # No response model as nothing to return
async def delete_user(user_id: int, current_user: current_user, db: Annotated[AsyncSession, Depends(get_db)]):
    if user_id != current_user.id:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Not authorized to delete the user"
                             )

    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)
    await db.commit()
