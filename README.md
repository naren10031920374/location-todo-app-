# Location-Based AI Todo App

A todo app that reminds you about a task when you are near the right store. You type a sentence like "milk, eggs and bread from Walmart tomorrow", and an LLM splits it into separate todos, categorizes them, and picks out the store and the date. The app then finds the nearest real branch of that store on OpenStreetMap, so the reminder fires when you are close.

The LLM only reads text. Deterministic code does everything else: it validates the output, saves the todos, finds the branch, and measures the distance to it. If the AI or the map lookup is down, the todo is still saved, just without that feature.

**Live demo:** <https://unrivaled-fox-6e7b39.netlify.app>. The API runs on Render's free tier, so the first request after 15 minutes idle can take 30 to 50 seconds while it wakes up.

| Step | What happens | Handled by |
|---|---|---|
| `parse` | One box takes free text. The LLM returns items, store, date and category as JSON | Groq (LLM) |
| `locate` | The store name is resolved to the closest branch within 15 km of you, and its coordinates are saved | OpenStreetMap Nominatim |
| `save` | One todo per item is created and linked to that store branch | FastAPI + PostgreSQL |
| `remind` | With **Location On**, the browser position is checked against saved branches, and a banner appears within about 1 km | Haversine distance in the API |

## Install on your phone

The frontend is a Progressive Web App, so the deployed site installs like a native app. There is no app store step.

- **Android (Chrome):** open the site, tap the menu, then **Install app** (or **Add to Home screen**).
- **iPhone (Safari):** open the site, tap **Share**, then **Add to Home Screen**.

It opens full screen with its own icon, and the app shell loads offline (todos still need a connection). Reminders fire only while the app is open, because a web app cannot track location in the background (see limitations below).

## Run it locally

Prerequisites: Python 3.12, Node.js, PostgreSQL with an empty database (for example `todo_db`), and optionally a free [Groq API key](https://console.groq.com/keys). Everything except the AI parsing works without the key.

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

cp .env.example .env           # Windows: copy .env.example .env
# edit .env: fill in DATABASE_URL, SECRET_KEY and LLM_API_KEY

python init_db.py              # creates the tables
python -m uvicorn main:app --reload
```

```bash
# Frontend (second terminal)
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000, with interactive docs at http://localhost:8000/docs
- App: http://localhost:5173

In the Swagger docs, click **Authorize** and enter your email and password. The protected endpoints use HTTP Basic auth.

Run the tests (40, with the LLM and map calls mocked, so no key or network is needed):

```bash
pip install pytest
pytest
```

## Try the demo script

Register an account, switch **Location Off** to **Location On**, allow the browser prompt, and add this:

> milk, eggs and bread from Walmart tomorrow

Expected results:

1. Three todos appear, each tagged `groceries`, with tomorrow's date.
2. The pop-up names the branch and how far away it is, for example `Walmart 1.2 km away`.
3. When your position is within about 1 km of that branch, the banner `You're near Walmart! 3 items on your list.` appears.

To test without leaving your desk, open Chrome DevTools, then **More tools**, then **Sensors**, and set a custom location. Use your own area to add the todo, then paste the coordinates of the Walmart shown in Google Maps to trigger the banner.

| Scenario | Result |
|---|---|
| Plain text with no store ("call mom") | Saved as one todo, categorized |
| Location blocked in the browser | Todos saved, store has no coordinates, no reminder |
| No branch of that store within 15 km | Todos saved, pop-up says no nearby branch was found |
| LLM unavailable or key missing | The text is saved as a single plain todo |

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | none (required) | PostgreSQL connection string. URL-encode special characters in the password (`@` becomes `%40`) |
| `SECRET_KEY` | none (required) | Signs JWTs. Generate a long random value and never commit it |
| `ALLOWED_ORIGINS` | local dev URLs | Comma-separated browser origins allowed by CORS. Set it to your frontend URL in production |
| `LLM_API_KEY` | none | API key for the LLM provider. `GROQ_API_KEY` also works |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Any OpenAI-compatible API |
| `LLM_MODEL` | `openai/gpt-oss-20b` | Model name sent to the provider |
| `NOMINATIM_URL` | public OpenStreetMap | Store-lookup endpoint |
| `NOMINATIM_USER_AGENT` | `LocationTodoApp/1.0 (...)` | Identifying User-Agent, required by the OSM usage policy. Set it to your own app name and contact |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `DEBUG` | `True` | `True` or `False` |

Frontend: `VITE_API_URL` is the API base URL (defaults to `http://localhost:8000`). It is read at build time.

The real `.env` file is git-ignored. Copy `backend/.env.example` and fill in your own values.

## How it works

```
 Browser (React PWA)                         FastAPI                         External
 ───────────────────                         ───────                         ────────
 types "milk from Walmart"
 + current position            ──POST /todos/create-from-text──▶  nlp_service.parse_todo_text ──▶ Groq
                                                                   (items, store, date, category)
                                                                   │
                                                                   ▼
                                                   services.get_or_create_store_near
                                                   1. saved branch within 15 km?  ──yes──▶ reuse
                                                   2. else geocoding.find_nearest_store ──▶ Nominatim
                                                   3. else store without coordinates
                                                                   │
                                                                   ▼
 pop-up: store + distance      ◀───────── todos + store ────────  one todo per item, linked to the branch

 Location On: watchPosition    ──POST /locations/nearby─────────▶  services.get_nearby_todos
 banner when near a store      ◀──────── nearby todos ──────────   (Haversine vs each branch)
```

- **Auth:** the API supports JWT login and HTTP Basic. The frontend stores the credentials locally and sends a Basic header on every request.
- **Store lookup:** the search is bounded to a box around you, so "Walmart" means the one near you rather than the one in another city. Results are throttled to one request per second and cached, as the Nominatim usage policy requires.
- **Reminders:** each todo-to-store link has its own distance threshold, 1 km by default. Completed todos and stores without coordinates are skipped.
- **Failure handling:** a failed AI call, a failed map lookup and a denied location each degrade to a simpler result instead of an error.

Code map:

```
backend/
  main.py            FastAPI app, routes, CORS
  nlp_service.py     LLM calls: parse text, classify category, suggest stores
  geocoding.py       Nominatim lookup (throttle, cache) and Haversine distance
  services.py        Users, todos, stores, store-to-todo links, nearby search
  models.py          SQLAlchemy models: User, TodoItem, Store, TodoStore
  schemas.py         Pydantic request and response models
  auth.py            Password hashing and JWT
  init_db.py         Creates the tables
  test_*.py          pytest suites
frontend/
  src/pages/         Login, Register, Todos (the one-box add form and tracking)
  src/api/client.js  Axios client with the auth header
  public/            PWA manifest, service worker, icons
netlify.toml         Netlify build and SPA routing
```

## Deployment

The live site uses Render for the API and database, and Netlify for the frontend, both on free plans.

**Backend (Render)**

1. Create a free **PostgreSQL** database and copy its URL.
2. Create a **Web Service** from this repo with root directory `backend`, build command `pip install -r requirements.txt`, and start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. Set the environment variables `DATABASE_URL`, `SECRET_KEY`, `LLM_API_KEY` and `ALLOWED_ORIGINS` (your Netlify URL).
4. Create the tables once by running `python init_db.py` from your machine with `DATABASE_URL` set to the database's external URL.
5. Check `https://<your-service>.onrender.com/health`.

**Frontend (Netlify)**

1. Import the repo. `netlify.toml` already sets the base directory, build command and SPA redirect.
2. Add the environment variable `VITE_API_URL` set to your Render URL, then deploy.

Free-plan limits:

- Render free web services sleep after 15 minutes idle, and the first request afterwards is slow.
- Render's free PostgreSQL expires 30 days after creation, with a short grace period. Move to another free host (Neon or Supabase) before then if you want to keep the data.
- Auto-deploy can be turned on in the Render service settings so a push redeploys the API.

## Design decisions and known limitations

- **LLM output is untrusted.** It is parsed as JSON, the classifier is restricted to a fixed category list, and anything that does not parse falls back to a plain todo.
- **Foreground location only.** The browser's location API works while the app is open. True background reminders need a native app, and the Capacitor route is the planned way to get that.
- **Public Nominatim is a shared service.** It is fine for a portfolio-scale app with user-triggered lookups. At real scale it should be replaced by a paid geocoder or self-hosted instance.
- **Matching the right branch** relies on the store name as typed. A chain with an unusual name or a store that is not in OpenStreetMap will not be found.
- **No migrations.** `init_db.py` only creates missing tables, so schema changes need a migration tool such as Alembic.
- **Credentials in local storage.** The web client keeps the Basic-auth credentials in the browser. A refresh-token flow with short-lived tokens would be safer.
- **No rate limiting** on the API yet.
