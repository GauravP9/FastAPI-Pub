from fastapi import FastAPI, Request, HTTPException, status, Depends    # Depends: Dependancy injection so we can inject db connection in our routes
from fastapi.templating import Jinja2Templates
from datetime import datetime
from fastapi.staticfiles import StaticFiles  # To serve the static files like CSS and images
from fastapi.exceptions import RequestValidationError   # Handle wrong request data like str instead of int passed
from starlette.exceptions import HTTPException as starletteHTTPException    # if someone access some route that are not present are catched by starlette exceptions
from typing import Annotated
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
from fastapi.exception_handlers import request_validation_exception_handler, http_exception_handler

import models
from database import Base, engine, get_db  # Base,engin - are for creating the tables and accessing, get_db for injection
from routers import posts, users    # Routers imported


# LIFESPAN FUNCTIONS
@asynccontextmanager    # Converts the function into a lifespan context manager.FASTAPI run code before startup and during shut wn
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)   # Creates all the tables which inherit from the Base class this is idempotent so even if we run multiple time no problems
    yield   # This is like pause button above code run before startup and below code run after startup

    # Shutdown
    await engine.dispose()

app = FastAPI(lifespan=lifespan)

app.mount('/static', StaticFiles(directory="static"), name="static")    # mount takes 3 args -> 1. URL path 2.static directory 3.Name we can use to ref in template
app.mount('/media', StaticFiles(directory="media"), name='media')    # This create /url route and help serve the user uploaded data


templates = Jinja2Templates(directory='templates')

app.include_router(users.router, prefix='/api/users', tags=['users'])   # Connect touter to app, prefix is added to router, tag creates collapasable section in docs
app.include_router(posts.router, prefix='/api/posts', tags=['posts'])


# If we want the same data on 2 routes we can stack the decorators
# include False then this will not show up in the documentation


@app.get('/', include_in_schema=False, name='home')  # name here is use for naming the route so that both route work seperately
@app.get('/posts', name='posts', include_in_schema=False)
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):  # request - allows us to return HTML via jinja template so whereve we use jinja template we use request as input
    result = await db.execute(      # selectinload -> eagerloading, this helps you to load relationship at the start only
        Select(models.Post).options(selectinload(models.Post.author))  # -> "While fetching posts, fetch the related authors too.
        .order_by(models.Post.date_posted.desc()))  # rough Xformation select(models.post) ->  Select * post order by date_posted desc
    posts=result.scalars().all()

    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})  # Here the posts is very important this lets us use the dict data to populate in the jinja template
    # Here the 1st keyword is what u used in jinja and 2nd keyword is value u want to give

# OUR API ROUTES SHOULD RETURN JSON /api
# OUR TEMPLATE ROUTES SHOULD RETURN HTML TEMPLATE - Frontend


@ app.get('/posts/{post_id}', status_code=status.HTTP_200_OK, include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically

    result=await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )

    post=result.scalars().first()
    if post:
        title=post.title[:50]
        return templates.TemplateResponse(
            request, "post.html",
            {"post": post, "title": title}
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")


@ app.get('/user/{user_id}/posts', include_in_schema=False, name='user_posts')
async def user_posts_page(request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result=await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )

    existing_userid=result.scalars().first()
    if not existing_userid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")

    result=await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))  # We are using author in the templates that is why this is needed
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc()))


    all_posts=result.scalars().all()
    # if all_posts:
    return templates.TemplateResponse(request,
                                      'user_posts.html', {
                                          'posts': all_posts,
                                          "user": existing_userid,
                                          "title": f"{existing_userid.username}'s Post"
                                      }
                                      )
    # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No post found by this userid")


@ app.exception_handler(starletteHTTPException)
async def general_http_exception(request: Request, exception: starletteHTTPException):

    if request.url.path.startswith('/api'):
        return await http_exception_handler(request, exception)

    message=(exception.detail
               if exception.detail
               else "An error occured check req and try again")

    return templates.TemplateResponse(request, 'error.html',
                                      {
                                          "status_code": exception.status_code,
                                          'title': exception.status_code,
                                          "message": message
                                      },
                                      status_code=exception.status_code)


@ app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith('/api'):
        return await request_validation_exception_handler(request, exception)

    return templates.TemplateResponse(
        request,
        'error.html',
        {
            'status_code': status.HTTP_422_UNPROCESSABLE_CONTENT,
            'title': status.HTTP_422_UNPROCESSABLE_CONTENT,
            'message': "Invalid req. Check the input and try again"
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
    )

# DUMMY FUN SO THAT ERROR STOPS THAT WAS CREATED DUE TO for_each fun in the jinja template


@ app.get('/account_page', include_in_schema=False)
async def account_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})


@ app.get('/login_page', include_in_schema=False)
async def login_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})


@ app.get('/register_page', include_in_schema=False)
async def register_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})
