from pydantic import BaseModel, ConfigDict, Field   # configdict - to configure models
from datetime import datetime

class PostBase(BaseModel):  # Base class - Will be use to create and receive post
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=2)
    author: str = Field(min_length=2, max_length=50)


class PostCreate(PostBase): # Whar we accept while creating post
    pass


class PostResponse(PostBase):  # What we return from our API
    model_config = ConfigDict(from_attributes=True) #Read data with object not just dict this is important for db reading->ORM

    id:int
    date_posted:str|datetime