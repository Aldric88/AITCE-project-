import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/axios";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const { setUser } = useAuth();
  const navigate = useNavigate();

  const login = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const body = new URLSearchParams();
      body.append("username", email);
      body.append("password", password);

      await api.post("/auth/login", body, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const me = await api.get("/auth/me");
      setUser(me.data);

      toast.success("Welcome back!");
      navigate("/dashboard");
    } catch (err) {
      console.error("Login error:", err);
      toast.error(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 flex items-center justify-center px-4 font-sans text-black dark:text-white page-enter">
      <div className="w-full max-w-md fade-in-up">
        {/* Logo/Brand */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-black dark:bg-white mb-6 scale-in">
            <span className="text-white dark:text-black font-bold text-3xl">N</span>
          </div>
          <h1 className="text-4xl font-black uppercase tracking-tighter mb-2">
            Notes Market
          </h1>
          <p className="text-gray-500 dark:text-zinc-400 uppercase tracking-wide text-sm font-bold">Welcome back</p>
        </div>

        {/* Login Form */}
        <div className="p-0">
          <form onSubmit={login} className="space-y-6">
            {/* Email */}
            <div className="fade-in stagger-1">
              <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-zinc-400 mb-2">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input-field rounded-none border-black dark:border-zinc-500 dark:bg-zinc-800 dark:text-white dark:placeholder-zinc-500 focus:ring-black dark:focus:ring-white"
                placeholder="you@college.ac.in"
              />
            </div>

            {/* Password */}
            <div className="fade-in stagger-2">
              <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 dark:text-zinc-400 mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="input-field rounded-none border-black dark:border-zinc-500 dark:bg-zinc-800 dark:text-white focus:ring-black dark:focus:ring-white"
                placeholder="••••••••"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full rounded-none h-12 text-sm font-bold tracking-widest hover:bg-gray-900 border border-transparent btn-ripple fade-in stagger-3"
            >
              {loading ? "SIGNING IN..." : "SIGN IN"}
            </button>
          </form>

          {/* Signup Link */}
          <div className="mt-8 text-center border-t border-gray-100 dark:border-zinc-800 pt-8">
            <p className="text-gray-500 dark:text-zinc-400 text-sm">
              Don't have an account?{" "}
              <Link
                to="/signup"
                className="font-bold text-black dark:text-white border-b-2 border-black dark:border-white hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-all pb-0.5"
              >
                Create one here
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-gray-400 dark:text-zinc-600 text-xs uppercase tracking-widest">
            Secure • Fast • Reliable
          </p>
        </div>
      </div>
    </div>
  );
}
