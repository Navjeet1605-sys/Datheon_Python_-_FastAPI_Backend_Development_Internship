# BookStore API - Task 1
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="BookStore API", description="Simple CRUD API for books")


# what a book looks like when the client sends it to us
class BookIn(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    author: str = Field(min_length=1, max_length=100)
    genre: Optional[str] = None
    price: float = Field(gt=0)
    year: int = Field(ge=1000, le=2100)


# what we send back (same as above plus an id)
class BookOut(BookIn):
    id: int


# no database for now, just a dictionary kept in memory
books = {}
next_id = 1


@app.get("/")
async def home():
    return {"message": "BookStore API is running, go to /docs"}


# CREATE
@app.post("/books", response_model=BookOut, status_code=201)
async def add_book(book: BookIn):
    global next_id

    new_book = BookOut(id=next_id, **book.model_dump())
    books[next_id] = new_book
    next_id += 1
    return new_book


# READ all nwith optional filters)
@app.get("/books", response_model=list[BookOut])
async def get_books(
    author: Optional[str] = None,
    genre: Optional[str] = None,
    max_price: Optional[float] = None,
):
    result = list(books.values())

    if author:
        result = [b for b in result if author.lower() in b.author.lower()]
    if genre:
        result = [b for b in result if b.genre and b.genre.lower() == genre.lower()]
    if max_price is not None:
        result = [b for b in result if b.price <= max_price]

    return result


# READ one
@app.get("/books/{book_id}", response_model=BookOut)
async def get_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")
    return books[book_id]


# UPDATE
@app.put("/books/{book_id}", response_model=BookOut)
async def update_book(book_id: int, book: BookIn):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")

    updated = BookOut(id=book_id, **book.model_dump())
    books[book_id] = updated
    return updated


# DELETE
@app.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int):
    if book_id not in books:
        raise HTTPException(status_code=404, detail="Book not found")

    del books[book_id]