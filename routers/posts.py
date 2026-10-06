from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from schemas import PostResponse, PostUpdate, PostCreate
import models
from auth import current_user


router = APIRouter()


@router.get('', response_model=list[PostResponse])  # By adding response model we validate what we are returning with the schemas
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc()),  # Ordered the post by desc so newest first
    )  # type: ignore
    posts = result.scalars().all()  # type: ignore
    if not posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return posts


@router.post('', response_model=PostCreate, status_code=status.HTTP_201_CREATED)
# Adding current user here even before any other thing checking if no valid token then error
async def create_post(post: PostCreate, current_user: current_user, db: Annotated[AsyncSession, Depends(get_db)]):
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=current_user.id  # Comes from the token
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=['author'])  # Will refresh post and load the author relations
    return new_post


@router.get('/{post_id}', status_code=status.HTTP_200_OK, response_model=PostResponse)
async def get_post(post_id: int,  db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically
    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    posts = result.scalars().first()
    if not posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return posts


# Used PostCreate cause the post that we modify and postcreate req same data and we doing full update so need same data as create
@router.put('/{post_id}',  status_code=status.HTTP_200_OK, response_model=PostResponse)  # Used put here so fun name is also modufy full
async def update_post_full(post_id: int, post_data: PostCreate, current_user: current_user, db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically
    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )   # Check if POST exists
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")

    if post.user_id != current_user.id:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Not authorized to update the post"
                             )

    post.title = post_data.title    # SET THE DATA
    post.content = post_data.content
    post.user_id = current_user.id

    await db.commit()  # How knows what to commit - Which objects have changed since they were loaded?
    await db.refresh(post)
    return post


# Used PostUpdate cause the post that we modify and PostUpdate req partial data
@router.patch('/{post_id}',  status_code=status.HTTP_200_OK, response_model=PostResponse)  # Used patch here so fun name is also partial
async def update_post_partial(post_id: int, post_data: PostUpdate, current_user: current_user, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.Post).where(models.Post.id == post_id)
    )   # Check if POST exists
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")

    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Not authorized to update the post"
                             )

    update_data = post_data.model_dump(exclude_unset=True)  # NOTE: This make PATCH work, This helps only get the updated data from the req body

    for field, val in update_data.items():   # Loop over dict
        setattr(post, field, val)   # Dynamical set the key,val on Post object

    await db.commit()  # How knows what to commit - Which objects have changed since they were loaded?
    await db.refresh(post, attribute_names=['author'])
    return post


@router.delete('/{post_id}', status_code=status.HTTP_204_NO_CONTENT)  # No response model as nothing to return
async def delete_post(post_id: int, current_user: current_user, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")

    if post.user_id != current_user.id:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Not authorized to update the post"
                             )

    await db.delete(post)
    await db.commit()
