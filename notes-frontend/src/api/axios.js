import axios from "axios";

const defaultApiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  `${window.location.protocol}//${window.location.hostname}:8001`;

export const TOKEN_KEY = "nm_access_token";

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setStoredToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

const api = axios.create({
  baseURL: defaultApiBaseUrl,
  withCredentials: true,
});

// Attach Bearer token to every request
api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) config.headers["Authorization"] = `Bearer ${token}`;
  return config;
});

// On 401 — clear token and redirect to login (no cookie-based refresh)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    const isAuthEndpoint =
      url.includes("/auth/login") ||
      url.includes("/auth/signup") ||
      url.includes("/auth/logout") ||
      url.includes("/auth/me") ||
      url.includes("/verify/");

    if (error?.response?.status === 401 && !isAuthEndpoint) {
      setStoredToken(null);
      window.location.href = "/login";
    }

    return Promise.reject(error);
  },
);

export default api;
