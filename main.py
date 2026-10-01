from fastapi import FastAPI, Request, HTTPException, status, Depends    # Depends: Dependancy injection so we can inject db connection in our routes
from fastapi.templating import Jinja2Templates
from datetime import datetime
from fastapi.staticfiles import StaticFiles  # To serve the static files like CSS and images
from fastapi.responses import JSONResponse  # We can manual return JSON responces
from fastapi.exceptions import RequestValidationError   # Handle wrong request data like str instead of int passed
from starlette.exceptions import HTTPException as starletteHTTPException    # if someone access some route that are not present are catched by starlette exceptions
from typing import Annotated
from sqlalchemy import Select
from sqlalchemy.orm import Session

import models
from database import Base, engine, get_db  # Base,engin - are for creating the tables and accessing, get_db for injection
from schemas import PostCreate, PostResponse, UserCreate, UserResponce

Base.metadata.create_all(bind=engine)   # Creates all the tables which inherit from the Base class this is idempotent so even if we run multiple time no problems


app = FastAPI()

app.mount('/static', StaticFiles(directory="static"), name="static")    # mount takes 3 args -> 1. URL path 2.static directory 3.Name we can use to ref in template
app.mount('/media', StaticFiles(directory="media"), name='media')    # This create /url route and help serve the user uploaded data


templates = Jinja2Templates(directory='templates')

# If we want the same data on 2 routes we can stack the decorators
# include False then this will not show up in the documentation


@app.get('/', include_in_schema=False, name='home')  # name here is use for naming the route so that both route work seperately
@app.get('/posts', name='posts')
def home(request: Request, db: Annotated[Session, Depends(get_db)]):  # request - allows us to return HTML via jinja template so whereve we use jinja template we use request as input
    result = db.execute(
        Select(models.Post)
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})  # Here the posts is very important this lets us use the dict data to populate in the jinja template
    # Here the 1st keyword is what u used in jinja and 2nd keyword is value u want to give

# OUR API ROUTES SHOULD RETURN JSON /api
# OUR TEMPLATE ROUTES SHOULD RETURN HTML TEMPLATE - Frontend


@app.get('/posts/{post_id}', status_code=status.HTTP_200_OK, include_in_schema=False)
def post_page(request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]):  # Do type hinting so we need not to do specifically

    result = db.execute(
        Select(models.Post).where(models.Post.id == post_id)
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
def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]):   # Create session and gives us and cleans afterwards
    result = db.execute(
        Select(models.User).where(models.User.username == user.username),
    )

    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This username already exists in the db"
                            )
    # EMAIL CHECKING
    email_result = db.execute(
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

    db.add(new_user)
    db.commit()
    db.refresh(new_user)    # reload the object from the db confirming commit

    return new_user


@app.get('/user/{user_id}/posts', include_in_schema=False, name='user_posts')
def user_posts_page(request: Request, user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        Select(models.User).where(models.User.id == user_id)
    )

    existing_userid = result.scalars().first()
    if not existing_userid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")

    result = db.execute(
        Select(models.Post).where(models.Post.user_id == user_id)
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
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]):  # Do type hinting so we need not to do specifically
    result = db.execute(
        Select(models.User).where(models.User.id == user_id)
    )

    existing_userid = result.scalars().first()

    if existing_userid:
        return existing_userid
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")


@app.get('/api/user/{user_id}/posts', response_model=list[PostResponse])
def get_post_of_user(user_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(
        Select(models.User).where(models.User.id == user_id)
    )

    existing_userid = result.scalars().first()
    if not existing_userid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User ID not found")

    result = db.execute(
        Select(models.Post).where(models.Post.user_id == user_id)
    )

    all_posts = result.scalars().all()
    # if all_posts:
    return all_posts
    # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No post found by this userid")


@app.get('/api/posts', response_model=list[PostResponse])  # By adding response model we validate what we are returning with the schemas
def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(Select(models.Post))
    posts = result.scalars().all()
    if not posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return posts


@app.post('/api/posts', response_model=PostCreate, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(Select(models.User).where(models.User.id == post.user_id))
    last_id = result.scalars().first()
    if not last_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User ID does not exist")

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@app.get('/api/posts/{post_id}', status_code=status.HTTP_200_OK, response_model=PostResponse)
def get_post(post_id: int,  db: Annotated[Session, Depends(get_db)]):  # Do type hinting so we need not to do specifically
    result = db.execute(Select(models.Post).where(models.Post.id == post_id))
    posts = result.scalars().first()
    if not posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")
    return posts


@app.exception_handler(starletteHTTPException)
def general_http_exception(request: Request, exception: starletteHTTPException):
    message = (exception.detail
               if exception.detail
               else "An error occured check req and try again")

    if request.url.path.startswith('/api'):
        return JSONResponse(status_code=exception.status_code, content={'detail': message})

    return templates.TemplateResponse(request, 'error.html',
                                      {
                                          "status_code": exception.status_code,
                                          'title': exception.status_code,
                                          "message": message
                                      },
                                      status_code=exception.status_code)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith('/api'):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={'detail': exception.errors()}
        )
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
def account_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})


@app.get('/login_page', include_in_schema=False)
def login_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})


@app.get('/register_page', include_in_schema=False)
def register_page(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})
