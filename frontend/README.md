# Location-Based Todo App - Frontend

A React web application for managing location-based todos with AI-powered task parsing.

## Features

- **User Authentication** - Register and login with email/password
- **Todo Management** - Create, view, and manage todos
- **AI Task Parsing** - Parse natural language to create todos automatically
- **Connected to Backend** - REST API integration with FastAPI backend
- **Responsive Design** - Works on desktop and mobile browsers

## Tech Stack

- **Framework**: React 18 with Vite
- **Styling**: CSS
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Routing**: React Router DOM

## Setup Instructions

### 1. Prerequisites

- Node.js 16+
- npm or yarn
- Running FastAPI backend at `http://localhost:8000`

### 2. Install Dependencies

```bash
npm install
```

### 3. Start Development Server

```bash
npm run dev
```

Frontend will be at `http://localhost:5173`

### 4. Build for Production

```bash
npm run build
```

## Project Structure

smart-todo-frontend/
├── src/
│ ├── api/
│ │ └── client.js # Axios HTTP client with Basic Auth
│ ├── services/
│ │ └── auth.js # Authentication functions
│ ├── pages/
│ │ ├── LoginPage.jsx # Login form
│ │ └── RegisterPage.jsx # Registration form
│ ├── styles/
│ │ └── Auth.css # Authentication UI styling
│ ├── App.jsx # Main app component with routing
│ ├── App.css # App styling
│ └── main.jsx # React entry point
├── package.json # Dependencies
├── vite.config.js # Vite configuration
└── README.md # This file

## Pages

### Login Page
- Email and password login
- Link to register page
- Stores credentials in localStorage
- Redirects to todos page on success

### Register Page
- Email, password, and confirm password fields
- Validation for matching passwords
- Link to login page
- Creates new user account

### Todos Page
- Display user's todos
- Logout button
- Placeholder for todo management UI

## API Integration

The frontend connects to FastAPI backend using Basic Auth:

1. User enters email/password in login/register form
2. Credentials sent to backend (`/auth/login` or `/auth/register`)
3. Credentials stored in localStorage
4. All future requests include `Authorization: Basic <credentials>` header
5. Backend validates credentials and processes request

## Authentication Flow

## Environment Variables

All configuration is in `src/api/client.js`:

```javascript
const API_BASE_URL = 'http://localhost:8000';
```

Change this to point to your backend URL.

## Development

### Hot Reload

Vite automatically reloads the page when you save code changes.

### Browser DevTools

Open browser DevTools (F12) to:
- Inspect components
- Check localStorage for credentials
- View network requests
- Debug JavaScript

## Troubleshooting

**Blank Page**: Check browser console for errors (F12)

**API Errors**: Ensure FastAPI backend is running at `http://localhost:8000`

**CORS Errors**: Backend needs CORS enabled (already configured)

**Authentication Failed**: Check email/password in backend database

## Future Features

- Todo list display
- Create new todos
- Edit/delete todos
- Location tracking
- AI-powered todo parsing
- Store management
- Real-time notifications

## Author

Naren - Portfolio Project for FANG-level positions

## License

MIT