from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import (
    Depends,  # Depends: Dependancy injection so we can inject db connection in our routes
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import (
    RequestValidationError,  # Handle wrong request data like str instead of int passed
)
from fastapi.staticfiles import (
    StaticFiles,  # To serve the static files like CSS and images
)
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import (
    HTTPException as starletteHTTPException,  # if someone access some route that are not present are catched by starlette exceptions
)

import models
from config import settings
from database import (
    # Base,  # Base,engin - are for creating the tables and accessing, get_db for injection
    engine,
    get_db,
)
from routers import posts, users  # Routers imported


# LIFESPAN FUNCTIONS
@asynccontextmanager  # Converts the function into a lifespan context manager.FASTAPI run code before startup and during shut wn
async def lifespan(_app: FastAPI):
    # Startup
    # Commented this while transitioning to postgres as we dont need to create table on start
    # async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.create_all)  # Creates all the tables which inherit from the Base class this is idempotent so even if we run multiple time no problems
    yield  # This is like pause button above code run before startup and below code run after startup

    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")  # mount takes 3 args -> 1. URL path 2.static directory 3.Name we can use to ref in template
# app.mount("/media", StaticFiles(directory="media"), name="media")  # Removed this as we are moved to AWS # This create /url route and help serve the user uploaded data


templates = Jinja2Templates(directory="templates")

app.include_router(users.router, prefix="/api/users", tags=["users"])  # Connect touter to app, prefix is added to router, tag creates collapasable section in docs
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


@app.get("/health")
async def health_check(db:Annotated[AsyncSession, Depends(get_db)]):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable"   
        ) from e
    return {"status":"healthy"}

# If we want the same data on 2 routes we can stack the decorators
# include False then this will not show up in the documentation


@app.get("/", include_in_schema=False, name="home")  # name is  for naming the route so that both route work seperately
@app.get("/posts", name="posts", include_in_schema=False)
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):  # request - allows us to return HTML via jinja template so whereve we use jinja template we use request as input

    count_result = await db.execute(select(func.count()).select_from(models.Post))  # Count syntax
    total_post_count = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))  # selectinload -> eagerloading, this helps you to load relationship at the start only
        .order_by(models.Post.date_posted.desc())  # Ordered the post by desc so newest first
        .limit(settings.post_per_page)
    )  # type: ignore

    posts = result.scalars().all()

    has_more = len(posts) < total_post_count  # len(current loaded posts) < total [10 < 50]

    return templates.TemplateResponse(
        request, "home.html", {"posts": posts, "title": "Home", "limit": settings.post_per_page, "has_more": has_more}
    )  # Here the posts is very important this lets us use the dict data to populate in the jinja template
    # Here the 1st keyword is what u used in jinja and 2nd keyword is value u want to give


# OUR API ROUTES SHOULD RETURN JSON /api
# OUR TEMPLATE ROUTES SHOULD RETURN HTML TEMPLATE - Frontend


@app.get("/posts/{post_id}", status_code=status.HTTP_200_OK, include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically

    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)).where(models.Post.id == post_id))

    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(request, "post.html", {"post": post, "title": title})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")


@app.get("/user/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    """Template route for returning all the post of a user"""

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    existing_userid = result.scalars().first()
    if not existing_userid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")

    count_result = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user_id),
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))  # We are using author in the templates that is why this is needed
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
        .limit(settings.post_per_page)
    )
    user_posts = result.scalars().all()

    has_more = len(user_posts) < total

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": user_posts,
            "user": existing_userid,
            "title": f"{existing_userid.username}'s Post",
            "limit":settings.post_per_page,
            "has_more":has_more
        },
    )
    # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No post found by this userid")


@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title": "Login"})


@app.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"title": "Register"})


@app.get("/account", include_in_schema=False)
async def account_page(request: Request):
    return templates.TemplateResponse(request, "account.html", {"title": "Account"})

@app.get("/forgot-password", include_in_schema=False)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"title": "Forgot Password"},
    )


@app.get("/reset-password", include_in_schema=False)
async def reset_password_page(request: Request):
    response = templates.TemplateResponse(
        request,
        "reset_password.html",
        {"title": "Reset Password"},
    )
    response.headers["Referrer-Policy"] = "no-referrer" # SecurityMeasure - refer passes header to other website where it is redirected from
    return response


@app.exception_handler(starletteHTTPException)
async def general_http_exception(request: Request, exception: starletteHTTPException):

    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = exception.detail if exception.detail else "An error occured check req and try again"

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid req. Check the input and try again",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
