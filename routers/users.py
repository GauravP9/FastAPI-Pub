from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, status  # Uploadfile - UploadFiles
from fastapi.security import OAuth2PasswordRequestForm
from PIL import UnidentifiedImageError  # For image error
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select  # func - for case-insensetive query[Any func called on this become sql func func.lower(col) => lower(col)]
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool
from botocore.exceptions import ClientError  # For error handling

import models
from auth import CurrentUser, create_access_token, generate_reset_token, hash_password, hash_reset_token, verify_password
from config import settings
from database import get_db
from email_utils import send_password_reset_email
from image_utils import process_profile_image, upload_profile_image, delete_profile_image
from schemas import ChangePasswordRequest, ForgotPasswordRequest, PaginatedPostResponse, PostResponse, ResetPasswordRequest, Token, UserCreate, UserPrivate, UserUpdate


router = APIRouter()


# Added prefix in main.py so all endpoint will become  /api/user/endpoint-name-in-this-page
@router.post("", response_model=UserPrivate, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):  # Create session and gives us and cleans afterwards
    result = await db.execute(
        select(models.User).where(func.lower(models.User.username) == user.username.lower()),
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This username already exists in the db")

    # EMAIL CHECKING
    email_result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == user.email.lower()),
    )
    existing_email = email_result.scalars().first()
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This email already exists in the db")

    new_user = models.User(username=user.username, email=user.email.lower(), password_hash=hash_password(user.password))

    db.add(new_user)  # No AWAIT here cause this only appends to session list
    await db.commit()
    await db.refresh(new_user)  # reload the object from the db confirming commit

    return new_user


@router.post("/token", status_code=status.HTTP_200_OK, response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[AsyncSession, Depends(get_db)]):
    # Look up user by email
    # NOTE: OAuth2 uses "username" field but we treat it as email

    result = await db.execute(select(models.User).where(func.lower(models.User.email) == form_data.username.lower()))

    user = result.scalars().first()

    # Verify user exist and password is correct

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)

    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=access_token_expires)
    return Token(access_token=access_token, token_type="bearer")


# OAuth2PasswordRequestForm - is a predefined FastAPI class that captures the login form fields (username, password, etc.) from the incoming HTTP request.
# is simply the value typed into the login form's username field (which in your application is being used as the email).


@router.get("/me", response_model=UserPrivate)  # This route for frontend to know who is logged in
async def get_current_user(current_user: CurrentUser):
    """Get the current authenticated user"""
    return current_user


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(password_data: ChangePasswordRequest, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    current_user.password_hash = hash_password(password_data.new_password)
    await db.execute(sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id == current_user.id))

    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)  # 202 we use accept here we dont confirm that this mail exist or not
async def forgot_password(request_data: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Annotated[AsyncSession, Depends(get_db)]):

    result = await db.execute(select(models.User).where(func.lower(models.User.email) == request_data.email.lower()))
    user = result.scalars().first()  # Check if user exists

    if user:
        await db.execute(sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id == user.id))  # Delete token if exist

        token = generate_reset_token()
        tokenhash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(settings.reset_token_expire_minutes)

        reset_token = models.PasswordResetToken(user_id=user.id, token_hash=tokenhash, expires_at=expires_at)

        db.add(reset_token)
        await db.commit()

        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,  # Sending token [As this will be need to login] not the hashed one we keep that in db
        )

    return {"message": "If an account exists with this email, you will receive password reset instructions"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,  # desrialization of incoming JSON
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token_hash = hash_reset_token(request_data.token)

    result = await db.execute(select(models.PasswordResetToken).where(models.PasswordResetToken.token_hash == token_hash))
    result_token = result.scalars().first()

    if not result_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    # if result_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):    # replace => sqlite bydefault strips out any tz related info so adding that back for comparison
    if result_token.expires_at < datetime.now(UTC):  # We dont need replace with pg as its tz aware
        await db.delete(result_token)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    result = await db.execute(select(models.User).where(models.User.id == result_token.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    user.password_hash = hash_password(request_data.new_password)

    await db.execute(sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id == user.id))

    await db.commit()  # All the dirty object are commited including updated password
    return {"message": "Password reset success"}


@router.get("/{user_id}", status_code=status.HTTP_200_OK, response_model=UserPrivate)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    existing_userid = result.scalars().first()

    if existing_userid:
        return existing_userid
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")


@router.get("/{user_id}/posts", response_model=PaginatedPostResponse)
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)], skip: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 10):
    """Get all the post of specific userid"""

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    existing_userid = result.scalars().first()
    if not existing_userid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")

    count_result = await db.execute(select(func.count()).select_from(models.Post).where(models.Post.user_id == user_id))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))  # Eagerloading-Required in API[Part of Model]
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()

    has_more = skip + len(posts) < total

    return PaginatedPostResponse(  # Paginated the results
        posts=[PostResponse.model_validate(post) for post in posts], total=total, skip=skip, limit=limit, has_more=has_more
    )


@router.patch("/{user_id}", status_code=status.HTTP_200_OK, response_model=UserPrivate)  # Used patch here so fun name is also partial
async def update_user_partial(user_id: int, user_update: UserUpdate, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):

    if user_id != current_user.id:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update the user")

    result = await db.execute(select(models.User).where(models.User.id == user_id))  # Check if USER exists
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User was not found")

    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(
            select(models.User).where(func.lower(models.User.username) == user_update.username.lower())  # Check if the new userid exists
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already present")

    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(select(models.User).where(func.lower(models.User.email) == user_update.email.lower()))  # Check if the new email exists
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already present")

    # update_data = user_update.model_dump(exclude_unset=True)  # NOTE: This make PATCH work, This helps only get the updated data from the req body

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email.lower()
    # if user_update.image_file is not None:  # Removed as part that any user could set image path of other user and delete it
    #     user.image_file = user_update.image_file

    await db.commit()  # How knows what to commit - Which objects have changed since they were loaded?
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)  # No response model as nothing to return
async def delete_user(user_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    if user_id != current_user.id:
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete the user")

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_filename = user.image_file  # Delete image file

    await db.delete(user)
    await db.commit()

    if old_filename:  # Waiting on commit first before deleting anything
        await delete_profile_image(old_filename)  # Await as new fun is async # Delete so that not to leave orphan file on the disc


@router.patch("/{user_id}/picture", response_model=UserPrivate)  # PATCH - Updating existing image
async def upload_profile_picture(
    user_id: int,
    file: UploadFile,  # UploadFile:HANDLING file upload browser sends this as MULTIPART form data instead of JSON. This gives special methods on the file
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
):
    """Endpoint to upload the image"""
    if current_user.id != user_id:  # Check authorization first
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user's picture")

    content = await file.read()  # Read the file

    if len(content) > settings.max_upload_size_bytes:  # file.size is not reliadble so len is done
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is too large max 5MB allowded")

    try:  # image processing is CPU Bound work - normally we do sync
        processed_byte, new_filename = await run_in_threadpool(process_profile_image, content=content)  # Offloads this to threadpool while keeping endpoint async

    except UnidentifiedImageError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file. Please upload the valid image file "
        ) from err  # "raise a new exception, but preserve err as the original cause."
        # Hide the old error from the user, but remember it as the root cause for debugging.

    # Upload to S3, runs in threadpool
    try:
        await upload_profile_image(processed_byte, new_filename)
    except ClientError as err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload the image. Try again !!") from err

    old_filename = current_user.image_file

    current_user.image_file = new_filename
    await db.commit()
    await db.refresh(current_user)

    if old_filename:
        await delete_profile_image(old_filename)  # We delete only on successful commit

    return current_user


@router.delete("{user_id}/picture", response_model=UserPrivate)
async def delete_user_picture(user_id: int, db: Annotated[AsyncSession, Depends(get_db)], current_user: CurrentUser):
    """Delete current user profile picture"""
    if current_user.id != user_id:  # Check authorization first
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this users picture")

    old_filename = current_user.image_file

    if old_filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No profile picture to delete")

    current_user.image_file = None  # Set the image file to NONE this will return the model's default image path

    await db.commit()
    await db.refresh(current_user)

    await delete_profile_image(old_filename)
    return current_user
