import apiClient from '../api/client';

export const authService = {
  // Register new user
  async register(email, password) {
    try {
      const response = await apiClient.post('/auth/register', {
        email,
        password,
      });
      
      // Store credentials in localStorage
      localStorage.setItem('email', email);
      localStorage.setItem('password', password);
      
      return response.data;
    } catch (error) {
      throw error.response?.data?.detail || 'Registration failed';
    }
  },

  // Login user
  async login(email, password) {
    try {
      const response = await apiClient.post('/auth/login', {
        email,
        password,
      });
      
      // Store credentials in localStorage
      localStorage.setItem('email', email);
      localStorage.setItem('password', password);
      
      return response.data;
    } catch (error) {
      throw error.response?.data?.detail || 'Login failed';
    }
  },

  // Logout user
  logout() {
    localStorage.removeItem('email');
    localStorage.removeItem('password');
  },

  // Check if user is logged in
  isLoggedIn() {
    return !!localStorage.getItem('email') && !!localStorage.getItem('password');
  },

  // Get current user info
  async getCurrentUser() {
    try {
      const response = await apiClient.get('/users/me');
      return response.data;
    } catch (error) {
      throw error.response?.data?.detail || 'Failed to get user info';
    }
  },
};