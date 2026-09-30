from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from datetime import datetime
from fastapi.staticfiles import StaticFiles
# To serve the static files like CSS and images

app = FastAPI()

app.mount('/static', StaticFiles(directory="static"), name="static")
# mount takes 3 args -> 1. URL path 2.static directory 3.Name we can use to ref in template


templates = Jinja2Templates(directory='templates')

posts: list[dict] = [
    {
        "id": 1,
        "author": "Gaurav Patil",
        "title": "Getting Started with Pydantic",
        "content": "Pydantic makes data validation and serialization simple in Python applications.",
        "date_posted": datetime(2018, 4, 20)
    },
    {
        "id": 2,
        "author": "Priya Sharma",
        "title": "Understanding FastAPI Dependency Injection",
        "content": "Dependency injection helps create reusable, testable, and maintainable APIs.",
        "date_posted": datetime(2018, 4, 20)
    },
    {
        "id": 3,
        "author": "Rahul Verma",
        "title": "Top 5 Python Tips",
        "content": "These Python tips can improve readability and reduce development time.",
        "date_posted": datetime(2018, 4, 20)
    },
    {
        "id": 4,
        "author": "Sneha Kulkarni",
        "title": "Introduction to SQLAlchemy",
        "content": "SQLAlchemy provides a powerful ORM for working with relational databases.",
        "date_posted": datetime(2018, 4, 20)
    },
    {
        "id": 5,
        "author": "Amit Joshi",
        "title": "REST vs GraphQL",
        "content": "Both REST and GraphQL are popular API architectures with unique benefits.",
        "date_posted": datetime(2018, 4, 20)
    }
]


# If we want the same data on 2 routes we can stack the decorators
# include False then this will not show up in the documentation

@app.get('/', include_in_schema=False, name='home')  # name here is use for naming the route so that both route work seperately
@app.get('/posts', name='posts')
def home(request: Request):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    return templates.TemplateResponse(request, "home.html", {"posts": posts, "title": "Home"})
    # Here the 1st keyword is what u used in jinja and 2nd keyword is value u want to give


@app.get('/api/posts')
def get_posts():
    return posts


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


@app.get('/user_posts/{user_id}', include_in_schema=False)
def user_posts(user_id):
    # Here the posts is very important this lets us use the dict data to populate in the jinja template
    pass
