from sqlalchemy.orm import Session
from models import User
from schemas import UserCreate
from auth import hash_password, verify_password

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