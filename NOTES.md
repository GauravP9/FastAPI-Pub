# 2nd commit

Templates direct created, we passed data to jinja via context dictonary and then we use for loop for itrating that data, We implemented templated inheritance added css, bootstarap for view. 
url_for - to generate url for both static file and routes

Here the request object which is used for rendering the jinja template have below properties as well
URL
Headers
Cookies
Query parameters
Client IP
HTTP method (GET, POST, etc.)

# 3rd commit - Query parameter, Error handling for API/TEMPLATE routes
Here we added a path parameter for the query and also introduced different error routes here as well which include validationerror, starletter exception handling,

 
# 4th commit - Pydantic Schemas
Schemas created for post here got to learn about the response model for validation, config dict
configDict is very improtant lets us access the object which are dict as attribute in the code


# 5th commit - SQLite convertsion
1.  BASE CLASS = "This class is an ORM model and should be mapped to a database table."
Base.metadata.create_all(...) -> Base keeps a collection of all ORM models that inherit from it and those are created in the database -> "Create all registered tables."

2.  models.py is creaed to set up the relationship between the tables and with the help of dependancy injection
model class is blueprint of the table -> select(model.post) -> "Query the table represented by the Post ORM class -> relation is cause _tablename_ = 'posts'

3.  In models whichever column has relationship mentioned those are just py relationship those are not real column and they r not converted to column either. VIMP relationship sqlalchemy dont create column for the one which have this relationship word
back_populates = "these two relationship fields represent the same connection"


4.  
We modified the apis , heavily used models here so that is very important
Models have mapped method which maps column to the attribute so it works as ORM
The queries are little different so need to focus on that 

# 6th commit - Async
@asynccontextmanager
lifespan context manager --> Enter context ↓ Use resource ↓ Exit context
A lifespan context manager is a function that lets FastAPI run setup code when the application starts and cleanup code when the application shuts down.

! To convert code into async
1.  Get asyncontextmanager which will create all the tables at the start of your application
2.  Now convert the database modesl into async with 
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
Here create the asyncsession and dependancy injection code

3.  EagerLoading - In async fun context lazy loading is not allowded meaning that we dont load other relationship automatically like its done in sync fun so here we have to use eagerloading meaning we tell fastapi that load relatioship at the start of the trasaction only

Converted to async engine, replaced sessionmaker async and get_db as well did 
main.py added lifespan and all route are now async and exception handler use fastapi default handler
for eagerloading we are using selectinload

# 7 commit - ROUTER


# 11 Authorization 
Authorization added no other user can edit anyones post
Ownership checks
Fronend forms working - copied this from the github
getcurrentuser function is the start of this tutorial see how does it functions

