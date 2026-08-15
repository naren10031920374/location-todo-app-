import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models import User, TodoItem, Store
from services import (
    create_user,
    authenticate_user,
    get_user_by_email,
    create_todo,
    get_user_todos,
    update_todo,
    delete_todo,
    create_store,
    get_all_stores,
)
from schemas import UserCreate, TodoItemCreate, TodoItemUpdate

# Create in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def test_db():
    """Create a test database and session"""
    engine = create_engine(
        SQLALCHEMY_TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    yield db
    db.close()

# ===== AUTH TESTS =====

def test_create_user(test_db):
    """Test user creation"""
    user_data = UserCreate(email="test@example.com", password="password123")
    user = create_user(test_db, user_data)
    
    assert user.email == "test@example.com"
    assert user.password_hash != "password123"  # Password should be hashed
    assert user.id is not None

def test_create_duplicate_user(test_db):
    """Test that duplicate emails are rejected"""
    user_data = UserCreate(email="test@example.com", password="password123")
    create_user(test_db, user_data)
    
    # Try to create another user with same email
    with pytest.raises(ValueError):
        create_user(test_db, user_data)

def test_authenticate_user(test_db):
    """Test user authentication"""
    user_data = UserCreate(email="test@example.com", password="password123")
    create_user(test_db, user_data)
    
    # Test with correct password
    authenticated_user = authenticate_user(test_db, "test@example.com", "password123")
    assert authenticated_user is not None
    assert authenticated_user.email == "test@example.com"
    
    # Test with wrong password
    wrong_user = authenticate_user(test_db, "test@example.com", "wrongpassword")
    assert wrong_user is None

def test_get_user_by_email(test_db):
    """Test getting user by email"""
    user_data = UserCreate(email="test@example.com", password="password123")
    create_user(test_db, user_data)
    
    user = get_user_by_email(test_db, "test@example.com")
    assert user is not None
    assert user.email == "test@example.com"

# ===== TODO TESTS =====

def test_create_todo(test_db):
    """Test todo creation"""
    # Create user first
    user_data = UserCreate(email="test@example.com", password="password123")
    user = create_user(test_db, user_data)
    
    # Create todo
    todo_data = TodoItemCreate(
        title="Buy milk",
        description="Get milk from store",
        category="groceries"
    )
    todo = create_todo(test_db, user.id, todo_data)
    
    assert todo.title == "Buy milk"
    assert todo.user_id == user.id
    assert todo.completed == False

def test_get_user_todos(test_db):
    """Test getting all todos for a user"""
    # Create user
    user_data = UserCreate(email="test@example.com", password="password123")
    user = create_user(test_db, user_data)
    
    # Create multiple todos
    todo1 = create_todo(test_db, user.id, TodoItemCreate(title="Buy milk"))
    todo2 = create_todo(test_db, user.id, TodoItemCreate(title="Buy eggs"))
    
    # Get all todos
    todos = get_user_todos(test_db, user.id)
    
    assert len(todos) == 2
    assert todo1 in todos
    assert todo2 in todos

def test_update_todo(test_db):
    """Test todo update"""
    # Create user and todo
    user_data = UserCreate(email="test@example.com", password="password123")
    user = create_user(test_db, user_data)
    
    todo = create_todo(test_db, user.id, TodoItemCreate(title="Buy milk"))
    
    # Update todo
    update_data = TodoItemUpdate(title="Buy milk and bread", completed=True)
    updated_todo = update_todo(test_db, todo.id, user.id, update_data)
    
    assert updated_todo.title == "Buy milk and bread"
    assert updated_todo.completed == True

def test_delete_todo(test_db):
    """Test todo deletion"""
    # Create user and todo
    user_data = UserCreate(email="test@example.com", password="password123")
    user = create_user(test_db, user_data)
    
    todo = create_todo(test_db, user.id, TodoItemCreate(title="Buy milk"))
    
    # Delete todo
    success = delete_todo(test_db, todo.id, user.id)
    assert success == True
    
    # Verify it's deleted
    todos = get_user_todos(test_db, user.id)
    assert len(todos) == 0

# ===== STORE TESTS =====

def test_create_store(test_db):
    """Test store creation"""
    store = create_store(
        test_db,
        name="Walmart",
        address="123 Main St",
        latitude=42.28,
        longitude=-83.74
    )
    
    assert store.name == "Walmart"
    assert store.latitude == 42.28

def test_get_all_stores(test_db):
    """Test getting all stores"""
    create_store(test_db, name="Walmart")
    create_store(test_db, name="Target")
    
    stores = get_all_stores(test_db)
    
    assert len(stores) == 2