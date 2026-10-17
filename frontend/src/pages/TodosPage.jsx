import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { authService } from '../services/auth';
import '../styles/Todos.css';

export default function TodosPage() {
  const [todos, setTodos] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [useAI, setUseAI] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Form states
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [aiText, setAiText] = useState('');
  const [creating, setCreating] = useState(false);
  
  // Location tracking state
  const [locationEnabled, setLocationEnabled] = useState(false);
  const [userLocation, setUserLocation] = useState(null);
  const [nearbyTodos, setNearbyTodos] = useState([]);
  const [showNotification, setShowNotification] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState('');

  // Fetch todos on component mount
  useEffect(() => {
    fetchTodos();
  }, []);

  // Setup location tracking
  useEffect(() => {
    if (!locationEnabled) return;

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setUserLocation({ latitude, longitude });
        checkNearbyTodos(latitude, longitude);
      },
      (err) => {
        setError(`Location error: ${err.message}`);
        setLocationEnabled(false);
      },
      { enableHighAccuracy: true, maximumAge: 5000 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, [locationEnabled]);

  // Fetch all todos
  const fetchTodos = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/todos');
      setTodos(response.data);
      setError('');
    } catch (err) {
      setError('Failed to load todos');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Check for nearby todos
  const checkNearbyTodos = async (latitude, longitude) => {
    try {
      const response = await apiClient.post('/locations/nearby', {
        latitude,
        longitude,
      });

      const { nearby_todos, count } = response.data;
      setNearbyTodos(nearby_todos);

      if (count > 0) {
        const store = nearby_todos[0].store_name;
        const message = `🛍️ You're near ${store}! ${count} item${count > 1 ? 's' : ''} on your list.`;
        showNotificationMessage(message);
      }
    } catch (err) {
      console.error('Location check error:', err);
    }
  };

  // Show notification
  const showNotificationMessage = (message) => {
    setNotificationMessage(message);
    setShowNotification(true);
    setTimeout(() => setShowNotification(false), 5000);
  };

  // Create todo (regular)
  const handleCreateTodo = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Title is required');
      return;
    }

    setCreating(true);
    try {
      await apiClient.post('/todos', {
        title: title.trim(),
        description: description.trim() || null,
        category: category || null,
      });

      setTitle('');
      setDescription('');
      setCategory('');
      setShowCreateForm(false);
      setError('');
      fetchTodos();
    } catch (err) {
      setError('Failed to create todo');
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  // Create todos with AI
  const handleCreateWithAI = async (e) => {
    e.preventDefault();
    if (!aiText.trim()) {
      setError('Please enter text to parse');
      return;
    }

    setCreating(true);
    try {
      const response = await apiClient.post('/todos/create-from-text', {
        text: aiText.trim(),
      });

      const { created_count, parsed_data } = response.data;
      setAiText('');
      setShowCreateForm(false);
      setError('');
      
      showNotificationMessage(`✨ Created ${created_count} todos from AI parsing!`);
      fetchTodos();
    } catch (err) {
      setError('Failed to parse text. Try: "I need milk, eggs, bread from Walmart tomorrow"');
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  // Update todo (mark complete)
  const handleToggleTodo = async (todo) => {
    try {
      await apiClient.put(`/todos/${todo.id}`, {
        completed: !todo.completed,
      });
      fetchTodos();
    } catch (err) {
      setError('Failed to update todo');
      console.error(err);
    }
  };

  // Delete todo
  const handleDeleteTodo = async (todoId) => {
    if (!confirm('Delete this todo?')) return;

    try {
      await apiClient.delete(`/todos/${todoId}`);
      fetchTodos();
    } catch (err) {
      setError('Failed to delete todo');
      console.error(err);
    }
  };

  // Handle logout
  const handleLogout = () => {
    authService.logout();
    window.location.href = '/login';
  };

  // Handle location toggle
  const handleLocationToggle = () => {
    if (!locationEnabled) {
      setLocationEnabled(true);
      showNotificationMessage('📍 Location tracking enabled');
    } else {
      setLocationEnabled(false);
      setUserLocation(null);
      setNearbyTodos([]);
      showNotificationMessage('📍 Location tracking disabled');
    }
  };

  return (
    <div className="todos-page">
      <header className="todos-header">
        <h1>📝 My Todos</h1>
        <div className="header-actions">
          <button
            className={`location-btn ${locationEnabled ? 'active' : ''}`}
            onClick={handleLocationToggle}
            title={locationEnabled ? 'Disable location' : 'Enable location tracking'}
          >
            📍 {locationEnabled ? 'Location On' : 'Location Off'}
          </button>
          <button onClick={handleLogout} className="logout-btn">
            Logout
          </button>
        </div>
      </header>

      {/* Notification */}
      {showNotification && (
        <div className="notification">
          {notificationMessage}
        </div>
      )}

      {/* Error message */}
      {error && <div className="error-message">{error}</div>}

      {/* User location info */}
      {userLocation && (
        <div className="location-info">
          📍 Your location: ({userLocation.latitude.toFixed(4)}, {userLocation.longitude.toFixed(4)})
          {nearbyTodos.length > 0 && (
            <div className="nearby-info">
              🛍️ {nearbyTodos.length} item{nearbyTodos.length > 1 ? 's' : ''} near you
            </div>
          )}
        </div>
      )}

      {/* Create form toggle */}
      <button
        className="create-btn"
        onClick={() => setShowCreateForm(!showCreateForm)}
      >
        {showCreateForm ? '✖ Cancel' : '➕ Add Todo'}
      </button>

      {/* Create todo form */}
      {showCreateForm && (
        <div className="create-form-container">
          <div className="form-tabs">
            <button
              className={`tab ${!useAI ? 'active' : ''}`}
              onClick={() => setUseAI(false)}
            >
              Manual
            </button>
            <button
              className={`tab ${useAI ? 'active' : ''}`}
              onClick={() => setUseAI(true)}
            >
              AI Parse
            </button>
          </div>

          {!useAI ? (
            <form onSubmit={handleCreateTodo} className="create-form">
              <input
                type="text"
                placeholder="Todo title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
              <textarea
                placeholder="Description (optional)"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows="3"
              />
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="">Select category (optional)</option>
                <option value="groceries">Groceries</option>
                <option value="pharmacy">Pharmacy</option>
                <option value="hardware">Hardware</option>
                <option value="clothing">Clothing</option>
                <option value="entertainment">Entertainment</option>
                <option value="other">Other</option>
              </select>
              <button type="submit" disabled={creating}>
                {creating ? 'Creating...' : 'Create Todo'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleCreateWithAI} className="create-form">
              <textarea
                placeholder="Example: I need milk, eggs, and bread from Walmart tomorrow"
                value={aiText}
                onChange={(e) => setAiText(e.target.value)}
                rows="3"
                required
              />
              <small>
                💡 Describe what you need, where, and when. AI will parse it!
              </small>
              <button type="submit" disabled={creating}>
                {creating ? 'Parsing...' : 'Parse with AI'}
              </button>
            </form>
          )}
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="loading">Loading todos...</div>
      ) : todos.length === 0 ? (
        <div className="empty-state">
          <p>No todos yet</p>
          <small>Create your first todo to get started!</small>
        </div>
      ) : (
        <div className="todos-list">
          {todos.map((todo) => (
            <div
              key={todo.id}
              className={`todo-card ${todo.completed ? 'completed' : ''}`}
            >
              <div className="todo-content">
                <input
                  type="checkbox"
                  checked={todo.completed}
                  onChange={() => handleToggleTodo(todo)}
                  className="todo-checkbox"
                />
                <div className="todo-info">
                  <h3>{todo.title}</h3>
                  {todo.description && <p>{todo.description}</p>}
                  <div className="todo-meta">
                    {todo.category && (
                      <span className="category-badge">{todo.category}</span>
                    )}
                    {todo.due_date && (
                      <span className="date-badge">
                        📅 {new Date(todo.due_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <button
                className="delete-btn"
                onClick={() => handleDeleteTodo(todo.id)}
                title="Delete todo"
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}