# Location-Based AI Todo App

A full-stack todo app that reminds you about tasks when you are near the right store, and uses a local LLM to turn natural language ("I need milk, eggs and bread from Walmart tomorrow") into categorized todos.

## Features

- Register and log in (JWT and HTTP Basic auth)
- Todo CRUD with categories and due dates
- Stores with address geocoding, linked to todos
- Location-based reminders using Haversine distance
- AI parsing, category classification and store suggestions powered by an LLM
- React web client with todo management and location tracking

## Repository layout

```
backend/    FastAPI + SQLAlchemy + PostgreSQL API
frontend/   React 19 + Vite web client
```

## Tech stack

| Layer | Tools |
|---|---|
| API | Python 3.12, FastAPI, Pydantic, SQLAlchemy |
| Database | PostgreSQL |
| Auth | JWT (python-jose), passlib/bcrypt |
| AI | Groq (OpenAI-compatible chat completions API) |
| Frontend | React, Vite, React Router, Axios, Zustand |

## Getting started

### Prerequisites

- Python 3.12
- Node.js
- PostgreSQL with an empty database (for example `todo_db`)
- A free [Groq API key](https://console.groq.com/keys) for the AI features (optional; everything else works without it)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

cp .env.example .env           # Windows: copy .env.example .env
# edit .env and fill in DATABASE_URL and SECRET_KEY

python init_db.py              # creates the tables
python -m uvicorn main:app --reload
```

The API runs at http://localhost:8000 and interactive docs are at http://localhost:8000/docs.

Run the tests:

```bash
pip install pytest
pytest
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173 and expects the API at http://localhost:8000.

## Backend environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string. URL-encode special characters in the password (`@` becomes `%40`). |
| `SECRET_KEY` | Secret used to sign JWTs. Generate a long random value and never commit it. |
| `LLM_API_KEY` | API key for the LLM provider (Groq by default). `GROQ_API_KEY` also works. |
| `LLM_BASE_URL` | Optional. Any OpenAI-compatible API. Defaults to `https://api.groq.com/openai/v1`. |
| `LLM_MODEL` | Optional. Defaults to `openai/gpt-oss-20b`. |
| `ENVIRONMENT` | `development` or `production` |
| `DEBUG` | `True` or `False` |

The real `.env` file is git-ignored. Copy `backend/.env.example` and fill in your own values.
