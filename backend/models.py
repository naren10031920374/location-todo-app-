from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# Users Table
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    todos = relationship("TodoItem", back_populates="user", cascade="all, delete-orphan")


# TodoItems Table
class TodoItem(Base):
    __tablename__ = "todo_items"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)  # e.g., "groceries", "pharmacy"
    due_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="todos")
    stores = relationship("Store", secondary="todo_store", back_populates="todos")


# Stores Table
class Store(Base):
    __tablename__ = "stores"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # e.g., "Walmart", "Kroger"
    address = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    todos = relationship("TodoItem", secondary="todo_store", back_populates="stores")


# TodoStore Join Table (links todos to stores)
class TodoStore(Base):
    __tablename__ = "todo_store"
    
    id = Column(Integer, primary_key=True, index=True)
    todo_id = Column(Integer, ForeignKey("todo_items.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    distance_threshold_km = Column(Float, default=1.0)  # Default: 1km reminder radius
    created_at = Column(DateTime, default=datetime.utcnow)