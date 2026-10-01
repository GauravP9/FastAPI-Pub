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
from schemas import PostCreate, PostResponse, UserCreate, UserResponce, PostUpdate, UserUpdate


# LIFESPAN FUNCTIONS
@asynccontextmanager    # Converts the function into a lifespan context manager.FASTAPI run code before startup and during shutdown
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

# If we want the same data on 2 routes we can stack the decorators
# include False then this will not show up in the documentation


@app.get('/', include_in_schema=False, name='home')  # name here is use for naming the route so that both route work seperately
@app.get('/posts', name='posts', include_in_schema=False)
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):  # request - allows us to return HTML via jinja template so whereve we use jinja template we use request as input
    result = await db.execute(
        # selectinload -> eagerloading, this helps you to load relationship at the start only
        Select(models.Post).options(selectinload(models.Post.author))  # -> "While fetching posts, fetch the related authors too.
    )  # rough Xformation select(models.post) ->  Select * post
    posts = result.scalars().all()

    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})  # Here the posts is very important this lets us use the dict data to populate in the jinja template
    # Here the 1st keyword is what u used in jinja and 2nd keyword is value u want to give

# OUR API ROUTES SHOULD RETURN JSON /api
# OUR TEMPLATE ROUTES SHOULD RETURN HTML TEMPLATE - Frontend


@app.get('/posts/{post_id}', status_code=status.HTTP_200_OK, include_in_schema=False)
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically

    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )

    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request, "post.html",
            {"post": post, "title": title}
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")


@app.post('/api/users', response_model=UserCreate, status_code=status.HTTP_201_CREATED)
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


@app.get('/user/{user_id}/posts', include_in_schema=False, name='user_posts')
async def user_posts_page(request: Request, user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )

    existing_userid = result.scalars().first()
    if not existing_userid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")

    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))  # We are using author in the templates that is why this is needed
        .where(models.Post.user_id == user_id)
    )

    all_posts = result.scalars().all()
    # if all_posts:
    return templates.TemplateResponse(request,
                                      'user_posts.html', {
                                          'posts': all_posts,
                                          "user": existing_userid,
                                          "title": f"{existing_userid.username}'s Post"
                                      }
                                      )
    # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No post found by this userid")


@app.get('/api/user/{user_id}', status_code=status.HTTP_200_OK, response_model=UserResponce)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically
    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )
    existing_userid = result.scalars().first()

    if existing_userid:
        return existing_userid
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")


@app.get('/api/user/{user_id}/posts', response_model=list[PostResponse])
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


@app.patch('/api/users/{user_id}',  status_code=status.HTTP_200_OK, response_model=UserResponce)  # Used patch here so fun name is also partial
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


@app.delete('/api/users/{user_id}', status_code=status.HTTP_204_NO_CONTENT)  # No response model as nothing to return
async def delete_user(user_id: int,  db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.User).where(models.User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)
    await db.commit()


@app.get('/api/posts', response_model=list[PostResponse])  # By adding response model we validate what we are returning with the schemas
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()
    if not posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return posts
    

@app.post('/api/posts', response_model=PostCreate, status_code=status.HTTP_201_CREATED)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.User)
        .where(models.User.id == post.user_id)
    )
    last_id = result.scalars().first()
    if not last_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID does not exist")

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id
    )

    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=['author'])  # Will refresh post and load the author relations
    return new_post


@app.get('/api/posts/{post_id}', status_code=status.HTTP_200_OK, response_model=PostResponse)
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
@app.put('/api/posts/{post_id}',  status_code=status.HTTP_200_OK, response_model=PostResponse)  # Used put here so fun name is also modufy full
async def update_post_full(post_id: int, post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):  # Do type hinting so we need not to do specifically
    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )   # Check if POST exists
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")

    if post_data.user_id == post.user_id:   # Check if the USER exists
        result = await db.execute(
            Select(models.User).where(models.User.id == post_data.user_id)
        )
        result_id = result.scalars().first()
        if not result_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID does not exist")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID does not have access to modify other users post")

    post.title = post_data.title    # SET THE DATA
    post.content = post_data.content
    post.user_id = post_data.user_id

    await db.commit()  # How knows what to commit - Which objects have changed since they were loaded?
    await db.refresh(post)
    return post


# Used PostUpdate cause the post that we modify and PostUpdate req partial data
@app.patch('/api/posts/{post_id}',  status_code=status.HTTP_200_OK, response_model=PostResponse)  # Used patch here so fun name is also partial
async def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.Post).where(models.Post.id == post_id)
    )   # Check if POST exists
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")

    update_data = post_data.model_dump(exclude_unset=True)  # NOTE: This make PATCH work, This helps only get the updated data from the req body

    for field, val in update_data.items():   # Loop over dict
        setattr(post, field, val)   # Dynamical set the key,val on Post object

    await db.commit()  # How knows what to commit - Which objects have changed since they were loaded?
    await db.refresh(post, attribute_names=['author'])
    return post


@app.delete('/api/posts/{post_id}', status_code=status.HTTP_204_NO_CONTENT)  # No response model as nothing to return
async def delete_post(post_id: int,  db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        Select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    await db.delete(post)
    await db.commit()


@app.exception_handler(starletteHTTPException)
async def general_http_exception(request: Request, exception: starletteHTTPException):
    
    if request.url.path.startswith('/api'):
        return await http_exception_handler(request, exception)
        
    message = (exception.detail
                   if exception.detail
                   else "An error occured check req and try again")
    

    return templates.TemplateResponse(request, 'error.html',
                                      {
                                          "status_code": exception.status_code,
                                          'title': exception.status_code,
                                          "message": message
                                      },
                                      status_code=exception.status_code)


@app.exception_handler(RequestValidationError)
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


@app.get('/account_page', include_in_schema=False)
async def account_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})


@app.get('/login_page', include_in_schema=False)
async def login_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})


@app.get('/register_page', include_in_schema=False)
async def register_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})
