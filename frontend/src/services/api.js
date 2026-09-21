import axios from 'axios';

const getApiBaseUrl = () => {
  const customHost = localStorage.getItem('metrix_api_server');
  if (customHost && customHost.trim()) {
    return customHost.trim().endsWith('/api/v1') ? customHost.trim() : `${customHost.trim().replace(/\/$/, '')}/api/v1`;
  }
  return import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
};

const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 120000,  // 2 min — YOLO + OCR inference can be slow on first load
});

api.interceptors.request.use(
  (config) => {
    config.baseURL = getApiBaseUrl();
    const token = localStorage.getItem('metrix_token') || localStorage.getItem('token') || sessionStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
