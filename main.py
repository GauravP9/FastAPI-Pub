from fastapi import FastAPI, Request, HTTPException, status
from fastapi.templating import Jinja2Templates
from datetime import datetime
from fastapi.staticfiles import StaticFiles  # To serve the static files like CSS and images
from fastapi.responses import JSONResponse  # We can manual return JSON responces
from fastapi.exceptions import RequestValidationError   # Handle wrong request data like str instead of int passed
from starlette.exceptions import HTTPException as starletteHTTPException    # if someone access some route that are not present are catched by starlette exceptions
from schemas import PostCreate, PostResponse

app = FastAPI()

app.mount('/static', StaticFiles(directory="static"), name="static")    # mount takes 3 args -> 1. URL path 2.static directory 3.Name we can use to ref in template


templates = Jinja2Templates(directory='templates')

posts: list[dict] = [
    {
        "id": 1,
        "author": "Gaurav Patil",
        "title": "Getting Started with Pydantic",
        "content": "Pydantic makes data validation and serialization simple in Python applications.",
        "date_posted": "Apr 1 2000"
    },
    {
        "id": 2,
        "author": "Priya Sharma",
        "title": "Understanding FastAPI Dependency Injection",
        "content": "Dependency injection helps create reusable, testable, and maintainable APIs.",
        "date_posted": "Apr 1 2000"
    },
    {
        "id": 3,
        "author": "Rahul Verma",
        "title": "Top 5 Python Tips",
        "content": "These Python tips can improve readability and reduce development time.",
        "date_posted": "Apr 1 2000"
    },
    {
        "id": 4,
        "author": "Sneha Kulkarni",
        "title": "Introduction to SQLAlchemy",
        "content": "SQLAlchemy provides a powerful ORM for working with relational databases.",
        "date_posted": "Apr 1 2000"
    },
    {
        "id": 5,
        "author": "Amit Joshi",
        "title": "REST vs GraphQL",
        "content": "Both REST and GraphQL are popular API architectures with unique benefits.",
        "date_posted": "Apr 1 2000"
    }
]


# If we want the same data on 2 routes we can stack the decorators
# include False then this will not show up in the documentation

@app.get('/', include_in_schema=False, name='home')  # name here is use for naming the route so that both route work seperately
@app.get('/posts', name='posts')
def home(request: Request):  # request - allows us to return HTML via jinja template so whereve we use jinja template we use request as input
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})  # Here the posts is very important this lets us use the dict data to populate in the jinja template
    # Here the 1st keyword is what u used in jinja and 2nd keyword is value u want to give

# OUR API ROUTES SHOULD RETURN JSON /api
# OUR TEMPLATE ROUTES SHOULD RETURN HTML TEMPLATE - Frontend


@app.get('/posts/{post_id}', status_code=status.HTTP_200_OK, include_in_schema=False)
def post_page(request: Request, post_id: int):  # Do type hinting so we need not to do specifically
    for post in posts:
        if post.get('id') == post_id:
            title = post.get('title')[:50]
            return templates.TemplateResponse(request, "post.html", {"post": post, "title": title})

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")


@app.get('/api/posts', response_model=list[PostResponse])  # By adding response model we validate what we are returning with the schemas
def get_posts():
    return posts


@app.post('/api/posts', response_model=PostCreate, status_code=status.HTTP_201_CREATED)
def create_post(post: PostCreate):
    new_id = max(p['id'] for p in posts) + 1 if posts else 1

    new_post = {
        "id": new_id,
        'author': post.author,
        'title': post.title,
        'content': post.content,
        'date_posted': 'Apr 1 2029'
    }

    posts.append(new_post)
    return new_post


@app.get('/api/posts/{post_id}', status_code=status.HTTP_200_OK, response_model=PostResponse)
def get_post(post_id: int):  # Do type hinting so we need not to do specifically
    for post in posts:
        if post.get('id') == post_id:
            return post

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post was not found")


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
