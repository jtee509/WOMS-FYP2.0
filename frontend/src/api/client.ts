import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  headers: {
    'Accept': 'application/json',
  },
});

// Request interceptor — inject JWT Bearer token from localStorage
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor — centralised error handling + 401 redirect
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data, config } = error.response;
      const detail = data?.detail || 'An unexpected error occurred';
      console.error(`[API ${status}] ${detail}`);

      // If 401 and not the login endpoint itself, clear token and redirect
      if (status === 401 && !config.url?.includes('/auth/login')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('auth_user');
        window.location.hash = '#/login';
      }
    } else if (error.request) {
      console.error('[API] No response received — is the backend running?');
    } else {
      console.error('[API]', error.message);
    }
    return Promise.reject(error);
  },
);

export default apiClient;
