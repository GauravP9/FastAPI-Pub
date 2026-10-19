from pydantic import BaseModel, ConfigDict, Field, EmailStr  # configdict - to configure models
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(max_length=50)
    email: EmailStr = Field(max_length=30)


class UserCreate(UserBase):
    password: str = Field(min_length=4)  # Accept passwd while creating


# ConfigDict - Pdantic when validating something default way is dict but with this method we READ fields from object attribute
# Pydantic extracts values from object attributes and then validates them. If we using pdantic everywhere then use from_attr


class UserPrivate:
    pass


# Splitted the UserResponse schema into Private/Public for appropriate use case


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # Read data with object not just dict this is important for db reading->ORM

    id: int
    username: str
    image_file: str | None
    image_path: str  # This is property of user model in model.py


class UserPrivate(UserPublic):
    email: EmailStr


class UserUpdate(UserBase):
    username: str | None = Field(default=None, max_length=50)  # Update here has all optional
    email: EmailStr | None = Field(default=None, max_length=30)
    # image_file: str | None = Field(default=None, max_length=100)  # User can set image_file of other as its value and then delete that through delete endpoint


class Token(BaseModel):
    access_token: str
    token_type: str


class PostBase(BaseModel):  # Base class - Will be use to create and receive post
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=2)
    # author: str = Field(min_length=2, max_length=50)    # We are removing this as this comes from the relationship


class PostCreate(PostBase):  # Whar we accept while creating post
    pass


class PostUpdate(PostBase):  # While updating the Post [Patch and Put method]
    title: str | None = Field(default=None, min_length=2, max_length=100)
    content: str | None = Field(default=None, min_length=2)


class PostResponse(PostBase):  # What we return from our API
    model_config = ConfigDict(from_attributes=True)  # Don't expect only dictionaries. You can also read values directly from object properties
    id: int  # || Read data with object not just dict this is important for db reading->ORM
    user_id: int
    date_posted: str | datetime
    author: UserPublic  # We will get neseted data here in post -> Updated this to UserPublic


class PaginatedPostResponse(BaseModel):  # For pagination
    posts: list[PostResponse]
    total: int  # Total Post
    skip: int  # Current Offset
    limit: int  # How many requested
    has_more: bool  # Whether more available


# PASSWORD RESET SCHEMAS
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=100)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=4)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=4)
