from pydantic import BaseModel, ConfigDict, Field, EmailStr   # configdict - to configure models
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(max_length=10)
    email: EmailStr = Field(max_length=30)


class UserCreate(UserBase):
    pass

# ConfigDict - Pdantic when validating something default way is dict but with this method we READ fields from object attribute
# Pydantic extracts values from object attributes and then validates them. If we using pdantic everywhere then use from_attr
class UserResponce(UserBase):
    model_config = ConfigDict(from_attributes=True)  # Read data with object not just dict this is important for db reading->ORM

    id: int
    image_file: str | None
    image_path: str     # This is property of user model in model.py


class UserUpdate(UserBase):
    username: str | None = Field(default=None, max_length=10)   # Update here has all optional
    email: EmailStr | None = Field(default=None, max_length=30)
    image_file: str | None = Field(default=None, max_length=100)


class PostBase(BaseModel):  # Base class - Will be use to create and receive post
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=2)
    # author: str = Field(min_length=2, max_length=50)    # We are removing this as this comes from the relationship


class PostCreate(PostBase):  # Whar we accept while creating post
    user_id: int  # Temporary


class PostUpdate(PostBase):  # While updating the Post [Patch and Put method]
    title: str | None = Field(default=None, min_length=2, max_length=100)
    content: str | None = Field(default=None, min_length=2)


class PostResponse(PostBase):  # What we return from our API
    model_config = ConfigDict(from_attributes=True)  # Read data with object not just dict this is important for db reading->ORM

    id: int
    user_id: int
    date_posted: str | datetime
    author: UserResponce  # We will get neseted data here with the post
