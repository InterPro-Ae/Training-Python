from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from typing import Optional

app=FastAPI()

class Book:
    id: int
    title: str
    author: str
    description: str
    rating: int

    def __init__(self, id, title, author, description, rating):
        self.id = id
        self.title= title
        self.author= author
        self.description= description
        self.rating= rating

class BookRequest(BaseModel):
    id: Optional[int] = Field(description='ID is not needed to create', default=None)##Makes the input optional
    title:str = Field(min_length=3)
    author:str = Field(min_length=1)
    description:str = Field(min_length=1, max_length=100)
    rating:int = Field(gt=0,lt=6)

    model_config= {
        "json_schema_extra":{
            "example":{
                "title":"a new book",
                "author":"yo mama",
                "description":"its a good book",
                "rating": 5
            }
        }
    }

BOOKS = [
    Book(1, 'Coding 1', 'Markos1','Good Stuff',5 ),
    Book(2, 'Coding 2', 'Markos2','Good Stuff',4 ),
    Book(3, 'Coding 3', 'Markos3','Good Stuff',3 ),
    Book(4, 'Coding 4', 'Markos4','Good Stuff',5 ),
    Book(5, 'Coding 5', 'Markos5','Good Stuff',2 ),
    Book(6, 'Coding 6', 'Markos6','Good Stuff',1 ),
]
## Retrieves books
@app.get("/books")
async def read_all_books():
    return BOOKS

## Returns the book with the id
@app.get("/books/{book_id}") 
async def read_book(book_id:int):
    for book in BOOKS:
        if book.id==book_id:
            return book
        
## Returns all the books with a rating
@app.get("/books/") 
async def read_book_by_rating(book_rating: int):
    books_to_return = []
    for book in BOOKS:
        if book.rating == book_rating:
            books_to_return.append(book)
    return books_to_return

## Creates a new book
@app.post("/create-book")
async def create_book(book_request:BookRequest):
    new_book= Book(**book_request.dict())
    BOOKS.append(find_book_id(new_book))

## Adding 1 to index
def find_book_id(book: Book):
    if len(BOOKS) > 0:
        book.id = BOOKS[-1].id +1
    else:
        book.id = 1

    return book

## Udpate stuff in books
@app.put("/books/update-book") 
async def update_book(book: BookRequest):
    for i in range(len(BOOKS)):
        if BOOKS[i].id ==book.id:
            BOOKS[i] = book


## Delete Book
@app.delete("/books/{book_id}")
async def delete_book(book_id:int):
    for i in range(len(BOOKS)):
        if BOOKS[i].id==book_id:
            BOOKS.pop(i)
            break    
