from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
import os

# Load environment variables
load_dotenv()

# Get SECRET_KEY from .env
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash a password
def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt"""
    return pwd_context.hash(password)

# Verify a password against its hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain password matches the hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

# Create JWT access token
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT token
    
    Args:
        data: Dictionary to encode in token (usually {"sub": user_id})
        expires_delta: How long the token is valid (default: 30 minutes)
    
    Returns:
        JWT token as a string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Verify JWT access token
def verify_token(token: str) -> dict:
    """
    Verify a JWT token and extract the payload
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload (dictionary with user info)
    
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise JWTError("Invalid or expired token")

# FastAPI security scheme
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    FastAPI dependency to get current user from JWT token
    
    Usage: Add 'current_user = Depends(get_current_user)' to your endpoint
    
    Args:
        credentials: HTTP Bearer token from request header
    
    Returns:
        Payload dictionary with user_id
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        return {"user_id": int(user_id)}
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

from fastapi.security import HTTPBasic, HTTPBasicCredentials

# Basic auth security
basic_security = HTTPBasic()

async def get_current_user_basic(credentials: HTTPBasicCredentials = Depends(basic_security)):
    """
    FastAPI dependency for basic authentication (email + password)
    
    Usage: Add 'current_user = Depends(get_current_user_basic)' to your endpoint
    
    Args:
        credentials: Email (username) and password from HTTP Basic Auth
    
    Returns:
        Payload dictionary with user_id
    
    Raises:
        HTTPException: If credentials are invalid
    """
    from database import SessionLocal
    from services import authenticate_user
    
    db = SessionLocal()
    try:
        # Email is the username in Basic Auth
        user = authenticate_user(db, credentials.username, credentials.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Basic"},
            )
        
        return {"user_id": user.id}
    
    finally:
        db.close()