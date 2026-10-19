from sqlalchemy import func
from sqlalchemy.orm import Session
from models import User
from schemas import UserCreate
from auth import hash_password, verify_password
from models import TodoItem, Store, TodoStore
from schemas import TodoItemCreate, TodoItemUpdate
from datetime import datetime
from models import Store
from geocoding import calculate_distance, find_nearest_store, SEARCH_RADIUS_KM

def get_user_by_email(db: Session, email: str):
    """Get a user from database by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    """Get a user from database by ID"""
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, user: UserCreate):
    """
    Create a new user in the database
    
    Args:
        db: Database session
        user: UserCreate schema with email and password
    
    Returns:
        Created User object
    
    Raises:
        ValueError: If email already exists
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise ValueError(f"Email {user.email} already registered")
    
    # Hash the password
    hashed_password = hash_password(user.password)
    
    # Create new user object
    db_user = User(
        email=user.email,
        password_hash=hashed_password
    )
    
    # Add to database and commit
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticate a user by email and password
    
    Args:
        db: Database session
        email: User email
        password: Plain password to verify
    
    Returns:
        User object if authentication succeeds, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user

# Get all todos for a specific user
def get_user_todos(db: Session, user_id: int):
    """Get all todos for a user"""
    return db.query(TodoItem).filter(TodoItem.user_id == user_id).all()

# Get a single todo by ID
def get_todo_by_id(db: Session, todo_id: int):
    """Get a single todo by ID"""
    return db.query(TodoItem).filter(TodoItem.id == todo_id).first()

# Create a new todo
def create_todo(db: Session, user_id: int, todo: TodoItemCreate):
    """
    Create a new todo for a user
    
    Args:
        db: Database session
        user_id: ID of the user creating the todo
        todo: TodoItemCreate schema with todo details
    
    Returns:
        Created TodoItem object
    """
    db_todo = TodoItem(
        user_id=user_id,
        title=todo.title,
        description=todo.description,
        category=todo.category,
        due_date=todo.due_date,
        completed=False
    )
    
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    
    return db_todo

# Update an existing todo
def update_todo(db: Session, todo_id: int, user_id: int, todo_update: TodoItemUpdate):
    """
    Update a todo
    
    Args:
        db: Database session
        todo_id: ID of todo to update
        user_id: ID of user (for authorization check)
        todo_update: TodoItemUpdate schema with new values
    
    Returns:
        Updated TodoItem object, or None if not found or unauthorized
    """
    db_todo = db.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.user_id == user_id
    ).first()
    
    if not db_todo:
        return None
    
    # Update only provided fields
    if todo_update.title is not None:
        db_todo.title = todo_update.title
    if todo_update.description is not None:
        db_todo.description = todo_update.description
    if todo_update.category is not None:
        db_todo.category = todo_update.category
    if todo_update.due_date is not None:
        db_todo.due_date = todo_update.due_date
    if todo_update.completed is not None:
        db_todo.completed = todo_update.completed
    
    db.commit()
    db.refresh(db_todo)
    
    return db_todo

# Delete a todo
def delete_todo(db: Session, todo_id: int, user_id: int):
    """
    Delete a todo
    
    Args:
        db: Database session
        todo_id: ID of todo to delete
        user_id: ID of user (for authorization check)
    
    Returns:
        True if deleted, False if not found or unauthorized
    """
    db_todo = db.query(TodoItem).filter(
        TodoItem.id == todo_id,
        TodoItem.user_id == user_id
    ).first()
    
    if not db_todo:
        return False
    
    db.delete(db_todo)
    db.commit()
    
    return True

# Get or create a store
def get_or_create_store(db: Session, name: str, latitude: float = None, longitude: float = None, address: str = None):
    """
    Get an existing store or create a new one
    
    Args:
        db: Database session
        name: Store name
        latitude: Store latitude (optional)
        longitude: Store longitude (optional)
        address: Store address (optional)
    
    Returns:
        Store object
    """
    store = db.query(Store).filter(Store.name == name).first()
    
    if store:
        return store
    
    db_store = Store(
        name=name,
        latitude=latitude,
        longitude=longitude,
        address=address
    )
    
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    
    return db_store

# Get or create a store that has no known location
def get_or_create_unlocated_store(db: Session, name: str):
    """
    Like get_or_create_store, but only reuses a store that has no coordinates.
    Used when we could not find which branch the user means, so we never silently
    attach their todo to some other city's branch.
    """
    store = db.query(Store).filter(
        func.lower(Store.name) == name.strip().lower(),
        Store.latitude.is_(None),
        Store.longitude.is_(None),
    ).first()
    if store:
        return store
    return create_store(db, name=name)

# Get or create the branch of a store that is near the user
def get_or_create_store_near(db: Session, name: str, user_latitude: float, user_longitude: float):
    """
    Find the branch of `name` closest to the user and return it as a Store with coordinates.

    Order of attempts:
      1. A branch of that name we already have saved within SEARCH_RADIUS_KM of the user (no network call).
      2. The nearest branch found on OpenStreetMap (Nominatim); it is saved for next time.
      3. Fall back to a plain store without coordinates (the old behaviour), so adding a todo never fails
         just because the lookup did.

    Returns:
        (store, distance_km). distance_km is None when no branch location could be found.
    """
    saved = db.query(Store).filter(
        func.lower(Store.name) == name.strip().lower(),
        Store.latitude.isnot(None),
        Store.longitude.isnot(None),
    ).all()

    best, best_distance = None, None
    for candidate in saved:
        d = calculate_distance(user_latitude, user_longitude, candidate.latitude, candidate.longitude)
        if d <= SEARCH_RADIUS_KM and (best is None or d < best_distance):
            best, best_distance = candidate, d
    if best:
        return best, round(best_distance, 2)

    found = find_nearest_store(name, user_latitude, user_longitude)
    if found:
        store = create_store(
            db,
            name=name,
            address=found["address"],
            latitude=found["latitude"],
            longitude=found["longitude"],
        )
        return store, found["distance_km"]

    return get_or_create_unlocated_store(db, name), None

# Get store by ID
def get_store_by_id(db: Session, store_id: int):
    """Get a store by ID"""
    return db.query(Store).filter(Store.id == store_id).first()

# Get all stores
def get_all_stores(db: Session):
    """Get all stores"""
    return db.query(Store).all()

# Create a new store
def create_store(db: Session, name: str, address: str = None, latitude: float = None, longitude: float = None):
    """
    Create a new store
    
    Args:
        db: Database session
        name: Store name
        address: Store address
        latitude: Store latitude
        longitude: Store longitude
    
    Returns:
        Created Store object
    """
    db_store = Store(
        name=name,
        address=address,
        latitude=latitude,
        longitude=longitude
    )
    
    db.add(db_store)
    db.commit()
    db.refresh(db_store)
    
    return db_store

# Link a todo to a store
def link_todo_to_store(db: Session, todo_id: int, store_id: int, distance_threshold_km: float = 1.0):
    """
    Link a todo to a store
    
    Args:
        db: Database session
        todo_id: ID of todo
        store_id: ID of store
        distance_threshold_km: Reminder distance threshold (default 1.0 km)
    
    Returns:
        Created TodoStore relationship
    """
    # Check if already linked
    existing = db.query(TodoStore).filter(
        TodoStore.todo_id == todo_id,
        TodoStore.store_id == store_id
    ).first()
    
    if existing:
        return existing
    
    db_todo_store = TodoStore(
        todo_id=todo_id,
        store_id=store_id,
        distance_threshold_km=distance_threshold_km
    )
    
    db.add(db_todo_store)
    db.commit()
    db.refresh(db_todo_store)
    
    return db_todo_store

# Remove a todo-store link
def unlink_todo_from_store(db: Session, todo_id: int, store_id: int):
    """
    Remove link between todo and store
    
    Returns:
        True if deleted, False if not found
    """
    db_todo_store = db.query(TodoStore).filter(
        TodoStore.todo_id == todo_id,
        TodoStore.store_id == store_id
    ).first()
    
    if not db_todo_store:
        return False
    
    db.delete(db_todo_store)
    db.commit()
    
    return True

def get_nearby_todos(db: Session, user_id: int, user_latitude: float, user_longitude: float, radius_km: float = 1.0):
    """
    Get all todos near the user's current location
    
    Args:
        db: Database session
        user_id: ID of the user
        user_latitude: User's current latitude
        user_longitude: User's current longitude
        radius_km: Search radius in kilometers (default 1.0 km)
    
    Returns:
        List of nearby todos with distance info
    """
    # Get all todos for this user
    todos = db.query(TodoItem).filter(
        TodoItem.user_id == user_id,
        TodoItem.completed == False  # Only incomplete todos
    ).all()
    
    nearby = []
    
    for todo in todos:
        # Get stores linked to this todo
        stores = todo.stores
        
        for store in stores:
            if store.latitude is None or store.longitude is None:
                continue
            
            # Calculate distance
            distance = calculate_distance(
                user_latitude,
                user_longitude,
                store.latitude,
                store.longitude
            )
            
            # Get the distance threshold for this todo-store pair
            todo_store = db.query(TodoStore).filter(
                TodoStore.todo_id == todo.id,
                TodoStore.store_id == store.id
            ).first()
            
            threshold = todo_store.distance_threshold_km if todo_store else radius_km
            
            # If within threshold, add to nearby list
            if distance <= threshold:
                nearby.append({
                    "todo_id": todo.id,
                    "todo_title": todo.title,
                    "store_id": store.id,
                    "store_name": store.name,
                    "distance_km": round(distance, 2),
                    "threshold_km": threshold
                })
    
    return nearby

def create_todos_from_parsed_text(db: Session, user_id: int, parsed_data: dict, store=None):
    """
    Create multiple todos from parsed natural language text
    
    Args:
        db: Database session
        user_id: ID of user creating todos
        parsed_data: Dictionary from NLP parsing with items, store, date, category
        store: Optional already-resolved Store (e.g. the branch near the user) to link the todos to.
               If omitted, a store is looked up or created from the parsed store name.
    
    Returns:
        List of created TodoItem objects
    """
    from datetime import datetime, timedelta
    
    items = parsed_data.get("items", [])
    store_name = parsed_data.get("store")
    date_str = parsed_data.get("date")
    category = parsed_data.get("category")
    
    created_todos = []
    
    # Create a store if store name is provided
    if store is None and store_name:
        store = get_or_create_store(db, store_name)
    
    # Parse date if provided (simple parsing for "tomorrow", "today", "next week")
    due_date = None
    if date_str:
        date_lower = date_str.lower()
        today = datetime.utcnow().date()
        
        if "tomorrow" in date_lower:
            due_date = datetime.combine(today + timedelta(days=1), datetime.min.time())
        elif "today" in date_lower:
            due_date = datetime.combine(today, datetime.min.time())
        elif "next week" in date_lower or "week" in date_lower:
            due_date = datetime.combine(today + timedelta(days=7), datetime.min.time())
    
    # Create a todo for each item
    for item in items:
        todo = TodoItemCreate(
            title=item,
            category=category,
            due_date=due_date
        )
        
        db_todo = create_todo(db, user_id, todo)
        
        # Link to store if store exists
        if store:
            link_todo_to_store(db, db_todo.id, store.id)
        
        created_todos.append(db_todo)
    
    return created_todos