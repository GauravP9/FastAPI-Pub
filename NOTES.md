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
models.py is creaed to set up the relationship between the tables and with the help of dependancy injection
We modified the apis , heavily used models here so that is very important
Models have mapped method which maps column to the attribute so it works as ORM
The queries are little different so need to focus on that 