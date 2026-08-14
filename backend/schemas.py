from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# TodoItem Schemas
class TodoItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    due_date: Optional[datetime] = None

class TodoItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: Optional[bool] = None

class TodoItemResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    due_date: Optional[datetime]
    completed: bool
    created_at: datetime
    user_id: int
    
    class Config:
        from_attributes = True

# Store Schemas
class StoreCreate(BaseModel):
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class StoreResponse(BaseModel):
    id: int
    name: str
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True

# TodoStore Schemas
class TodoStoreCreate(BaseModel):
    todo_id: int
    store_id: int
    distance_threshold_km: Optional[float] = 1.0

class TodoStoreResponse(BaseModel):
    id: int
    todo_id: int
    store_id: int
    distance_threshold_km: float
    created_at: datetime
    
    class Config:
        from_attributes = True