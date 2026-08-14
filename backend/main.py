from fastapi import FastAPI, HTTPException, status, Depends
from sqlalchemy.orm import Session
from schemas import UserCreate, UserResponse
from services import create_user, authenticate_user
from auth import create_access_token
from database import get_db
from auth import get_current_user

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