from database import engine, Base
from models import User, TodoItem, Store, TodoStore

# Create all tables based on models
Base.metadata.create_all(bind=engine)

print("✅ Database tables created successfully!")
print("Tables created:")
print("  - users")
print("  - todo_items")
print("  - stores")
print("  - todo_store")