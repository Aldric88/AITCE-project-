import axios from "axios";

const defaultApiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  `${window.location.protocol}//${window.location.hostname}:8000`;

const api = axios.create({
  baseURL: defaultApiBaseUrl,
  withCredentials: true,
});
const refreshClient = axios.create({
  baseURL: defaultApiBaseUrl,
  withCredentials: true,
});

let isRefreshing = false;
let queued = [];

const resolveQueue = (error) => {
  queued.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve();
  });
  queued = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const url = original?.url || "";
    const isAuthEndpoint =
      url.includes("/auth/refresh") ||
      url.includes("/auth/login") ||
      url.includes("/auth/signup") ||
      url.includes("/auth/logout");

    if (error?.response?.status !== 401 || original?._retry || isAuthEndpoint) {
      return Promise.reject(error);
    }

    original._retry = true;
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        queued.push({
          resolve: async () => {
            try {
              resolve(await api(original));
            } catch (err) {
              reject(err);
            }
          },
          reject,
        });
      });
    }

    isRefreshing = true;
    try {
      await refreshClient.post("/auth/refresh");
      resolveQueue(null);
      return api(original);
    } catch (refreshErr) {
      resolveQueue(refreshErr);
      return Promise.reject(refreshErr);
    } finally {
      isRefreshing = false;
    }
  },
);

export default api;
