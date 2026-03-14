import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { AuthProvider } from "./auth/AuthContext.jsx";
import { ThemeProvider } from "./context/ThemeContext.jsx";
import toast, { Toaster } from "react-hot-toast";
import "./index.css";

// Prevent the same error toast from appearing more than once per 30 seconds
const ERROR_TOAST_DEDUPE_MS = 30000;
const errorToastSeenAt = new Map();
const rawToastError = toast.error.bind(toast);

toast.error = (message, options = {}) => {
  const msg = typeof message === "string" ? message : "Something went wrong";
  const key = options?.id ? `id:${options.id}` : `msg:${msg}`;
  const now = Date.now();
  const last = errorToastSeenAt.get(key) || 0;
  if (now - last < ERROR_TOAST_DEDUPE_MS) return options?.id || key;
  errorToastSeenAt.set(key, now);
  return rawToastError(message, options);
};

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <App />
        <Toaster
          position="top-right"
          reverseOrder={false}
          gutter={8}
          toastOptions={{
            duration: 3000,
            style: { maxWidth: "360px", fontSize: "13px" },
            success: { duration: 2500 },
            error: { duration: 4000 },
          }}
        />
      </AuthProvider>
    </ThemeProvider>
  </React.StrictMode>
);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", async () => {
    if (import.meta.env.DEV) {
      // Avoid stale cache issues during local development.
      const registrations = await navigator.serviceWorker.getRegistrations();
      await Promise.all(registrations.map((r) => r.unregister()));
      return;
    }

    navigator.serviceWorker.register("/sw.js").catch(() => {
      // ignore SW registration failures.
    });
  });
}
