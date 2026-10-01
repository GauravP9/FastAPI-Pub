from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from schemas import PostResponse, UserCreate, UserResponce, UserUpdate
import models

router = APIRouter()


# we will add prefix in main.py so withing user.py will have empty string and at end it will add up and become /api/user
@router.post("", response_model=UserCreate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):   # Create session and gives us and cleans afterwards
    result = await db.execute(
        Select(models.User).where(models.User.username == user.username),
    )

    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This username already exists in the db"
                            )
    # EMAIL CHECKING
    email_result = await db.execute(
        Select(models.User).where(models.User.email == user.email),
    )

    existing_email = email_result.scalars().first()

    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This email already exists in the db"
                            )

    new_user = models.User(
        username=user.username,
        email=user.email
    )

    db.add(new_user)    # No AWAIT here cause this only appends to session list
    await db.commit()
    await db.refresh(new_user)    # reload the object from the db confirming commit

    return new_user


@router.get('/{user_id}', status_code=status.HTTP_200_OK, response_model=UserResponce)
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
    )

    all_posts = result.scalars().all()
    # if all_posts:
    return all_posts
    # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No post found by this userid")


@router.patch('/{user_id}',  status_code=status.HTTP_200_OK, response_model=UserResponce)  # Used patch here so fun name is also partial
async def update_user_partial(user_id: int, user_update: UserUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )   # Check if USER exists
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")

    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(
            Select(models.User).where(models.User.username == user_update.username)  # Check if the new userid exists
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already present")

    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(
            Select(models.User).where(models.User.email == user_update.email)
        )   # Check if the new email exists
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already present")

    update_data = user_update.model_dump(exclude_unset=True)  # NOTE: This make PATCH work, This helps only get the updated data from the req body

    for field, val in update_data.items():   # Loop over dict
        setattr(user, field, val)   # Dynamical set the key,val on Post object

    await db.commit()  # How knows what to commit - Which objects have changed since they were loaded?
    await db.refresh(user)
    return user


@router.delete('/{user_id}', status_code=status.HTTP_204_NO_CONTENT)  # No response model as nothing to return
async def delete_user(user_id: int,  db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)
    await db.commit()
