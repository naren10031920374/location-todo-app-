from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    """Root endpoint - returns a welcome message"""
    return {"message": "Welcome to Location-Based Todo App"}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}