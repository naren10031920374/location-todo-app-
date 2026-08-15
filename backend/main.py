from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, status, Depends
from sqlalchemy.orm import Session
from schemas import UserCreate, UserResponse
from services import create_user, authenticate_user
from auth import create_access_token
from database import get_db
from auth import get_current_user
from schemas import TodoItemCreate, TodoItemUpdate, TodoItemResponse
from services import (
    create_todo, 
    get_user_todos, 
    get_todo_by_id, 
    update_todo, 
    delete_todo,
    link_todo_to_store,
    unlink_todo_from_store,
    get_or_create_store,
    get_store_by_id,
    get_all_stores,
    create_store
)
from schemas import StoreCreate, StoreResponse
from geocoding import calculate_distance
from services import get_nearby_todos

app = FastAPI()

@app.get("/")
def read_root():
    """Root endpoint - returns a welcome message"""
    return {"message": "Welcome to Location-Based Todo App"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/auth/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    User registration endpoint
    
    Args:
        user: UserCreate schema with email and password
        db: Database session (injected automatically)
    
    Returns:
        Created user response
    
    Raises:
        HTTPException: If email already exists
    """
    try:
        db_user = create_user(db, user)
        return db_user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/auth/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    """
    User login endpoint
    
    Args:
        user: UserCreate schema with email and password
        db: Database session (injected automatically)
    
    Returns:
        JWT access token
    
    Raises:
        HTTPException: If email or password is incorrect
    """
    # Authenticate user
    db_user = authenticate_user(db, user.email, user.password)
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create JWT token
    access_token = create_access_token(data={"sub": str(db_user.id)})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

from auth import get_current_user

@app.get("/users/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Protected endpoint - requires valid JWT token
    
    To use this:
    1. Login to get access_token
    2. In Swagger, click "Authorize" button (lock icon at top right)
    3. Paste: Bearer <your_access_token>
    4. Now you can access this endpoint
    
    Args:
        current_user: Current user info from JWT token (injected by Depends)
    
    Returns:
        Current user information
    """
    return {
        "user_id": current_user["user_id"],
        "message": f"Hello user {current_user['user_id']}"
    }

# ===== TODO ENDPOINTS =====

@app.post("/todos", response_model=TodoItemResponse)
def create_new_todo(todo: TodoItemCreate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a new todo
    
    Requires authentication.
    
    Args:
        todo: TodoItemCreate schema with title and optional details
        current_user: Current authenticated user (from JWT)
        db: Database session
    
    Returns:
        Created TodoItem
    """
    user_id = current_user["user_id"]
    db_todo = create_todo(db, user_id, todo)
    return db_todo

@app.get("/todos", response_model=list[TodoItemResponse])
def list_user_todos(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all todos for the current user
    
    Requires authentication.
    
    Returns:
        List of user's todos
    """
    user_id = current_user["user_id"]
    todos = get_user_todos(db, user_id)
    return todos

@app.get("/todos/{todo_id}", response_model=TodoItemResponse)
def get_single_todo(todo_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get a single todo by ID
    
    Requires authentication. Only the todo owner can view their own todos.
    
    Args:
        todo_id: ID of the todo
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        TodoItem object
    
    Raises:
        HTTPException: If todo not found or user not authorized
    """
    user_id = current_user["user_id"]
    db_todo = get_todo_by_id(db, todo_id)
    
    if not db_todo or db_todo.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    return db_todo

@app.put("/todos/{todo_id}", response_model=TodoItemResponse)
def update_existing_todo(todo_id: int, todo_update: TodoItemUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update a todo
    
    Requires authentication. Only the todo owner can update their todos.
    
    Args:
        todo_id: ID of the todo to update
        todo_update: TodoItemUpdate schema with new values
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Updated TodoItem
    
    Raises:
        HTTPException: If todo not found or user not authorized
    """
    user_id = current_user["user_id"]
    db_todo = update_todo(db, todo_id, user_id, todo_update)
    
    if not db_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found or unauthorized"
        )
    
    return db_todo

@app.delete("/todos/{todo_id}")
def delete_existing_todo(todo_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Delete a todo
    
    Requires authentication. Only the todo owner can delete their todos.
    
    Args:
        todo_id: ID of the todo to delete
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Confirmation message
    
    Raises:
        HTTPException: If todo not found or user not authorized
    """
    user_id = current_user["user_id"]
    success = delete_todo(db, todo_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found or unauthorized"
        )
    
    return {"message": "Todo deleted successfully"}

@app.post("/todos/{todo_id}/stores/{store_id}")
def link_todo_to_store_endpoint(todo_id: int, store_id: int, distance_threshold_km: float = 1.0, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Link a todo to a store (for location-based reminders)
    
    Args:
        todo_id: ID of the todo
        store_id: ID of the store
        distance_threshold_km: Reminder distance (default 1.0 km)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Confirmation message
    """
    user_id = current_user["user_id"]
    
    # Verify todo belongs to user
    db_todo = get_todo_by_id(db, todo_id)
    if not db_todo or db_todo.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    link_todo_to_store(db, todo_id, store_id, distance_threshold_km)
    
    return {"message": f"Todo {todo_id} linked to store {store_id}"}

@app.delete("/todos/{todo_id}/stores/{store_id}")
def unlink_todo_from_store_endpoint(todo_id: int, store_id: int, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Remove link between a todo and a store
    
    Args:
        todo_id: ID of the todo
        store_id: ID of the store
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Confirmation message
    """
    user_id = current_user["user_id"]
    
    # Verify todo belongs to user
    db_todo = get_todo_by_id(db, todo_id)
    if not db_todo or db_todo.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    success = unlink_todo_from_store(db, todo_id, store_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )
    
    return {"message": f"Todo {todo_id} unlinked from store {store_id}"}

# ===== STORE ENDPOINTS =====

@app.post("/stores", response_model=StoreResponse)
def create_new_store(store: StoreCreate, db: Session = Depends(get_db)):
    """
    Create a new store
    
    Args:
        store: StoreCreate schema with store details
        db: Database session
    
    Returns:
        Created Store
    """
    db_store = create_store(
        db,
        name=store.name,
        address=store.address,
        latitude=store.latitude,
        longitude=store.longitude
    )
    return db_store

@app.get("/stores", response_model=list[StoreResponse])
def list_all_stores(db: Session = Depends(get_db)):
    """
    Get all stores
    
    Returns:
        List of all stores
    """
    stores = get_all_stores(db)
    return stores

@app.get("/stores/{store_id}", response_model=StoreResponse)
def get_single_store(store_id: int, db: Session = Depends(get_db)):
    """
    Get a single store by ID
    
    Args:
        store_id: ID of the store
    
    Returns:
        Store object
    
    Raises:
        HTTPException: If store not found
    """
    db_store = get_store_by_id(db, store_id)
    
    if not db_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Store not found"
        )
    
    return db_store

# ===== LOCATION ENDPOINTS =====

class LocationUpdate(BaseModel):
    """Location update from mobile app"""
    latitude: float
    longitude: float

@app.post("/locations/nearby")
def check_nearby_todos(location: LocationUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Check if user is near any of their todos
    
    This endpoint is called by the mobile app when the user's location changes.
    
    Args:
        location: Current user location (latitude, longitude)
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of nearby todos with distance info
    """
    user_id = current_user["user_id"]
    
    nearby_todos = get_nearby_todos(
        db,
        user_id,
        location.latitude,
        location.longitude
    )
    
    return {
        "user_location": {
            "latitude": location.latitude,
            "longitude": location.longitude
        },
        "nearby_todos": nearby_todos,
        "count": len(nearby_todos)
    }