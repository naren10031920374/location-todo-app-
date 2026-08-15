import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import { authService } from './services/auth';
import './App.css';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    setIsLoggedIn(authService.isLoggedIn());
    setLoading(false);
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/todos"
          element={isLoggedIn ? <TodosPage /> : <Navigate to="/login" />}
        />
        <Route path="/" element={<Navigate to={isLoggedIn ? "/todos" : "/login"} />} />
      </Routes>
    </BrowserRouter>
  );
}

// Simple todos page placeholder
function TodosPage() {
  const handleLogout = () => {
    authService.logout();
    window.location.href = '/login';
  };

  return (
    <div className="todos-container">
      <h1>📝 My Todos</h1>
      <button onClick={handleLogout}>Logout</button>
      <p>Coming soon: Todo management interface</p>
    </div>
  );
}

export default App;