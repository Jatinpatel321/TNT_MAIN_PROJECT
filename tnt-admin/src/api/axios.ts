import axios from 'axios';
import { AUTH_STORAGE_KEY, useAuthStore } from '../store/authStore';
import toast from 'react-hot-toast';

const BASE_URL = 'http://localhost:8000';
let redirectingToLogin = false;

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── Request Interceptor — Attach JWT ─────────────────────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response Interceptor — Error Handling ────────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      // Network error
      toast.error('Cannot reach server — check if backend is running', {
        id: 'network-error',
        duration: 4000,
      });
      return Promise.reject(error);
    }

    const { status } = error.response;

    if (status === 401) {
      useAuthStore.getState().logout();
      window.localStorage.removeItem(AUTH_STORAGE_KEY);

      if (window.location.pathname !== '/login' && !redirectingToLogin) {
        redirectingToLogin = true;
        window.location.replace('/login');
      }

      return Promise.reject(error);
    }

    if (status === 403) {
      toast.error("You don't have permission to do this", {
        id: 'forbidden',
      });
      return Promise.reject(error);
    }

    if (status === 503) {
      // Dispatch custom event for emergency banner
      window.dispatchEvent(new CustomEvent('campus-shutdown', {
        detail: { message: error.response.data?.detail || 'Campus services suspended' }
      }));
      return Promise.reject(error);
    }

    // Generic error with backend message
    const message = error.response?.data?.detail || error.response?.data?.message || 'Something went wrong';
    toast.error(message, { id: `error-${status}` });

    return Promise.reject(error);
  }
);

export default api;
