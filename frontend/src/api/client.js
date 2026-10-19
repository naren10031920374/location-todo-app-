import axios from 'axios';

// Base URL for the FastAPI backend. Set VITE_API_URL at build time (for example in
// Netlify's environment variables); falls back to the local dev server.
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

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