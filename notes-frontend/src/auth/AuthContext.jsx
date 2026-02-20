import { createContext, useContext, useEffect, useState } from "react";
import api from "../api/axios";

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const fetchMe = async () => {
      try {
        const res = await api.get("/auth/me");
        if (active) setUser(res.data);
      } catch {
        if (active) setUser(null);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchMe();
    return () => {
      active = false;
    };
  }, []);

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // no-op: clear local auth state even if backend call fails
    }
    setUser(null);
  };

  const refreshUser = async () => {
    try {
      const res = await api.get("/auth/me");
      setUser(res.data);
    } catch {
      setUser(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <div className="text-center">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center border border-black bg-black">
            <span className="text-2xl font-bold text-white">N</span>
          </div>
          <p className="text-sm font-bold uppercase tracking-wide text-gray-500">Loading</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, setUser, loading, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);
