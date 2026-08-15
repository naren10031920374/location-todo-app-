import axios from 'axios';

// Base URL for your FastAPI backend
const API_BASE_URL = 'http://localhost:8000';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add interceptor to include auth credentials in requests
apiClient.interceptors.request.use((config) => {
  const email = localStorage.getItem('email');
  const password = localStorage.getItem('password');
  
  if (email && password) {
    // Add Basic Auth header
    const credentials = btoa(`${email}:${password}`);
    config.headers.Authorization = `Basic ${credentials}`;
  }
  
  return config;
});

export default apiClient;