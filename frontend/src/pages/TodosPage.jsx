import { useState, useEffect } from 'react';
import apiClient from '../api/client';
import { authService } from '../services/auth';
import '../styles/Todos.css';

export default function TodosPage() {
  const [todos, setTodos] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Add-todo form state (one box: AI parses and categorizes whatever you type)
  const [text, setText] = useState('');
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

  // Where is the user right now? Used to find the nearest branch of the store they typed.
  // Reuses live tracking if it is on; otherwise asks the browser once (cached for 5 minutes).
  // Resolves to null if location is unavailable or denied, and adding a todo carries on without it.
  const getCurrentLocation = () => {
    if (userLocation) return Promise.resolve(userLocation);
    if (!('geolocation' in navigator)) return Promise.resolve(null);
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
        () => resolve(null),
        { timeout: 5000, maximumAge: 300000 }
      );
    });
  };

  // Add todo(s): the AI splits the text into items and picks the category, store and date.
  // If the AI is unavailable or finds no items (e.g. "call mom"), the text is saved as one
  // normal todo, so adding something never depends on the AI being up.
  const handleAddTodo = async (e) => {
    e.preventDefault();
    const input = text.trim();
    if (!input) {
      setError('Type what you need to do');
      return;
    }

    setCreating(true);
    setError('');
    try {
      let created = 0;
      let category = null;
      let aiWorked = true;
      let store = null;
      let sentLocation = false;

      try {
        const where = await getCurrentLocation();
        sentLocation = !!where;
        const response = await apiClient.post('/todos/create-from-text', {
          text: input,
          ...(where ? { latitude: where.latitude, longitude: where.longitude } : {}),
        });
        created = response.data.created_count || 0;
        category = response.data.todos?.[0]?.category || null;
        store = response.data.store || null;
      } catch (aiErr) {
        aiWorked = false; // AI unavailable or couldn't parse it: fall back below
        console.warn('AI parsing failed, saving as a plain todo:', aiErr);
      }

      if (created === 0) {
        let fallbackCategory = null;
        if (aiWorked) {
          try {
            const response = await apiClient.post('/ai/classify-todo', { text: input });
            fallbackCategory = response.data.category || null;
          } catch {
            // no category is fine
          }
        }
        await apiClient.post('/todos', { title: input, category: fallbackCategory });
        created = 1;
        category = fallbackCategory;
      }

      setText('');
      setShowCreateForm(false);
      let message = `✨ Added ${created} todo${created > 1 ? 's' : ''}${category ? ` · ${category}` : ''}`;
      if (store?.located) {
        message += ` · 📍 ${store.name} ${store.distance_km != null ? `${store.distance_km} km away` : 'found nearby'}`;
      } else if (store) {
        message += sentLocation
          ? ` · ${store.name} (couldn't find a nearby branch, so no reminder)`
          : ` · ${store.name} (allow location access to get a reminder)`;
      }
      showNotificationMessage(message);
      fetchTodos();
    } catch (err) {
      setError('Failed to add todo');
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
          <form onSubmit={handleAddTodo} className="create-form">
            <textarea
              placeholder="What do you need? e.g. milk, eggs and bread from Walmart tomorrow"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows="3"
              autoFocus
              required
            />
            <small>
              💡 Type it naturally. Items, store and date are picked out and categorized automatically.
            </small>
            <button type="submit" disabled={creating}>
              {creating ? 'Adding...' : 'Add'}
            </button>
          </form>
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