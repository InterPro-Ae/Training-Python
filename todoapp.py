from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import sqlite3
from contextlib import contextmanager

app = FastAPI(title="Todo API", description="A simple Todo API with SQLite database")

# Database setup
DATABASE_NAME = "todos.db"

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    """Initialize the database with todos table"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed BOOLEAN DEFAULT 0,
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert some dummy data if table is empty
        cursor.execute("SELECT COUNT(*) as count FROM todos")
        count = cursor.fetchone()["count"]

        if count == 0:
            dummy_todos = [
                ("Buy groceries", "Milk, eggs, bread, and coffee", 0, "high", "2026-09-22"),
                ("Finish FastAPI project", "Complete the todo API with database", 0, "high", "2026-09-25"),
                ("Read a book", "Start reading the new Python book", 0, "low", "2026-09-30"),
                ("Workout", "30 minutes cardio", 1, "medium", "2026-09-21"),
                ("Call mom", "Check in with family", 0, "medium", "2026-09-23"),
            ]

            cursor.executemany(
                "INSERT INTO todos (title, description, completed, priority, due_date) VALUES (?, ?, ?, ?, ?)",
                dummy_todos
            )

# Initialize database on startup
init_db()

# Pydantic models
class TodoBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    completed: bool = False
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    due_date: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Complete project documentation",
                "description": "Write API documentation for the todo app",
                "completed": False,
                "priority": "high",
                "due_date": "2026-09-25"
            }
        }
    }

class TodoCreate(TodoBase):
    pass

class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    completed: Optional[bool] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    due_date: Optional[str] = None

class TodoResponse(TodoBase):
    id: int
    created_at: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "Complete project documentation",
                "description": "Write API documentation for the todo app",
                "completed": False,
                "priority": "high",
                "due_date": "2026-09-25",
                "created_at": "2026-09-21 10:30:00"
            }
        }
    }

# Helper function to convert sqlite Row to dict
def row_to_dict(row):
    """Convert sqlite3.Row to dictionary"""
    return {key: row[key] for key in row.keys()}

# API Endpoints

@app.get("/")
async def root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to Todo API",
        "endpoints": {
            "GET /todos": "Get all todos",
            "GET /todos/{todo_id}": "Get a specific todo",
            "GET /todos/status/{completed}": "Get todos by completion status",
            "POST /todos": "Create a new todo",
            "PUT /todos/{todo_id}": "Update a todo",
            "DELETE /todos/{todo_id}": "Delete a todo"
        }
    }

@app.get("/todos", response_model=List[TodoResponse])
async def get_all_todos():
    """Get all todos"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM todos ORDER BY created_at DESC")
        todos = [row_to_dict(row) for row in cursor.fetchall()]
        return todos

@app.get("/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: int):
    """Get a specific todo by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        todo = cursor.fetchone()

        if not todo:
            raise HTTPException(status_code=404, detail=f"Todo with id {todo_id} not found")

        return row_to_dict(todo)

@app.get("/todos/status/{completed}", response_model=List[TodoResponse])
async def get_todos_by_status(completed: bool):
    """Get todos by completion status"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM todos WHERE completed = ? ORDER BY created_at DESC", (int(completed),))
        todos = [row_to_dict(row) for row in cursor.fetchall()]
        return todos

@app.get("/todos/priority/{priority}", response_model=List[TodoResponse])
async def get_todos_by_priority(priority: str):
    """Get todos by priority level"""
    if priority not in ["low", "medium", "high"]:
        raise HTTPException(status_code=400, detail="Priority must be 'low', 'medium', or 'high'")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM todos WHERE priority = ? ORDER BY created_at DESC", (priority,))
        todos = [row_to_dict(row) for row in cursor.fetchall()]
        return todos

@app.post("/todos", response_model=TodoResponse, status_code=201)
async def create_todo(todo: TodoCreate):
    """Create a new todo"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO todos (title, description, completed, priority, due_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (todo.title, todo.description, int(todo.completed), todo.priority, todo.due_date)
        )

        todo_id = cursor.lastrowid
        cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        new_todo = cursor.fetchone()

        return row_to_dict(new_todo)

@app.put("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    """Update a todo"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if todo exists
        cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        existing_todo = cursor.fetchone()

        if not existing_todo:
            raise HTTPException(status_code=404, detail=f"Todo with id {todo_id} not found")

        # Build update query dynamically based on provided fields
        update_fields = []
        update_values = []

        if todo_update.title is not None:
            update_fields.append("title = ?")
            update_values.append(todo_update.title)

        if todo_update.description is not None:
            update_fields.append("description = ?")
            update_values.append(todo_update.description)

        if todo_update.completed is not None:
            update_fields.append("completed = ?")
            update_values.append(int(todo_update.completed))

        if todo_update.priority is not None:
            update_fields.append("priority = ?")
            update_values.append(todo_update.priority)

        if todo_update.due_date is not None:
            update_fields.append("due_date = ?")
            update_values.append(todo_update.due_date)

        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        update_values.append(todo_id)
        query = f"UPDATE todos SET {', '.join(update_fields)} WHERE id = ?"

        cursor.execute(query, update_values)

        # Fetch and return updated todo
        cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        updated_todo = cursor.fetchone()

        return row_to_dict(updated_todo)

@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int):
    """Delete a todo"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if todo exists
        cursor.execute("SELECT * FROM todos WHERE id = ?", (todo_id,))
        todo = cursor.fetchone()

        if not todo:
            raise HTTPException(status_code=404, detail=f"Todo with id {todo_id} not found")

        cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))

        return {"message": f"Todo with id {todo_id} deleted successfully"}

@app.patch("/todos/{todo_id}/toggle")
async def toggle_todo_completion(todo_id: int):
    """Toggle the completion status of a todo"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if todo exists
        cursor.execute("SELECT completed FROM todos WHERE id = ?", (todo_id,))
        todo = cursor.fetchone()

        if not todo:
            raise HTTPException(status_code=404, detail=f"Todo with id {todo_id} not found")

        # Toggle completion status
        new_status = not bool(todo["completed"])
        cursor.execute("UPDATE todos SET completed = ? WHERE id = ?", (int(new_status), todo_id))

        return {"message": f"Todo {todo_id} completion status toggled to {new_status}"}
