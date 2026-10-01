from __future__ import annotations
from datetime import UTC, datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

# from config import settings


class User(Base):   # Set here cause we want to assossiate the post with each user
    __tablename__ = "users"  # Very imp if not referenced then while creating the table in metadata will show error
    # Mapped and mapped_column lets you connect a var to a db connection
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)  # Mapped is generic type hint used by alchemy to indicate that attribute is mapped to db
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=True)
    image_file: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
    )

    posts: Mapped[list[Post]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",   # delete-orphan -> This mean that if user is deleted then all the post are deleted as well
    )   # One to Many relationship. Here post can be connected to many user
    # Post here is forward reference - before creating post[class created below ] we can ref

    @property   # decorator that lets you access a method like an attribute
    def image_path(self) -> str:
        if self.image_file:
            return f"/media/profile_pics/{self.image_file}"  # This is user uploaded data we storing in media so create that folder and serve them as static file
        return "/static/profile_pics/default.jpg"


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),  # We are referencing the user.id here against post
        nullable=False,
        index=True,
    )
    date_posted: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    likes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    author: Mapped[User] = relationship(back_populates="posts")  # One to many relationship -> Links this relationship to the posts relationship in the User model:


# One User can have many Posts
# One Post belongs to exactly one User

# Because author is an ORM relationship attribute, not a database column.
# The ORM creates author so you don't have to manually query the users table every time you want information about the user who owns a post. 
# That's one of the biggest benefits of using an ORM.

# mapped_column(...) → becomes a database column ✅
# relationship(...) → becomes a Python object reference ✅
# relationship(...) never creates a table column ❌

# ┌─────────────────────┐
# │       users         │
# ├─────────────────────┤
# │ id (PK)             │◄────────────┐
# │ username            │             │
# │ email               │             │
# │ password_hash       │             │
# │ image_file          │             │
# └─────────────────────┘             │
#          │                          │
#          │ user.posts               │ post.author
#          │                          │
#          ▼                          │
# ┌─────────────────────┐             │
# │       posts         │─────────────┘
# ├─────────────────────┤
# │ id (PK)             │
# │ title               │
# │ content             │
# │ user_id (FK)        │ ──► users.id
# │ date_posted         │
# │ likes               │
# └─────────────────────┘
