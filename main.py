from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse  # To return HTML to frontend while loading the routes
from fastapi.templating import Jinja2Templates


app = FastAPI()


from datetime import datetime

posts: list[dict] = [
    {
        "id": 1,
        "author": "Gaurav Patil",
        "title": "Getting Started with Pydantic",
        "content": "Pydantic makes data validation and serialization simple in Python applications.",
        "date_posted": datetime(2026, 9, 15, 10, 30)
    },
    {
        "id": 2,
        "author": "Priya Sharma",
        "title": "Understanding FastAPI Dependency Injection",
        "content": "Dependency injection helps create reusable, testable, and maintainable APIs.",
        "date_posted": datetime(2026, 9, 16, 14, 45)
    },
    {
        "id": 3,
        "author": "Rahul Verma",
        "title": "Top 5 Python Tips",
        "content": "These Python tips can improve readability and reduce development time.",
        "date_posted": datetime(2026, 9, 17, 9, 15)
    },
    {
        "id": 4,
        "author": "Sneha Kulkarni",
        "title": "Introduction to SQLAlchemy",
        "content": "SQLAlchemy provides a powerful ORM for working with relational databases.",
        "date_posted": datetime(2026, 9, 18, 11, 20)
    },
    {
        "id": 5,
        "author": "Amit Joshi",
        "title": "REST vs GraphQL",
        "content": "Both REST and GraphQL are popular API architectures with unique benefits.",
        "date_posted": datetime(2026, 9, 19, 16, 10)
    }
]

@app.get('/posts', response_class= HTMLResponse)    #If we want the same data on 2 routes we can stack the decorators
@app.get('/', response_class= HTMLResponse, include_in_schema= False)   #include False then this will not show up in the documentation 
def root():
    return f"<h1> {posts[0]['title']}</h1>"

@app.get('/api/posts')
def get_posts():
    return posts