import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/axios";

console.log("Signup.jsx loaded");

export default function Signup() {
  console.log("Signup component rendering");
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    dept: "CSE",
    year: 3,
    section: "G1",
  });

  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: name === "year" ? parseInt(value, 10) || p.year : value }));
  };

  const signup = async () => {
    try {
      await api.post("/auth/signup", form);
      alert("Signup successful ✅ Now login.");
      navigate("/login");
    } catch (err) {
      alert(err.response?.data?.detail || "Signup failed");
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900/40 p-8">
        <h2 className="text-3xl font-bold text-center mb-6">Sign Up</h2>

        <div className="space-y-4">
          <input
            className="w-full px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
            name="name"
            placeholder="Name"
            value={form.name}
            onChange={handleChange}
          />
          <input
            className="w-full px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
            name="email"
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={handleChange}
          />
          <input
            className="w-full px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
            name="password"
            type="password"
            placeholder="Password (min 6 chars)"
            value={form.password}
            onChange={handleChange}
          />

          <div className="grid grid-cols-3 gap-3">
            <input
              className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
              name="dept"
              placeholder="Dept"
              value={form.dept}
              onChange={handleChange}
            />
            <input
              className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
              name="year"
              type="number"
              placeholder="Year"
              value={form.year}
              onChange={handleChange}
            />
            <input
              className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
              name="section"
              placeholder="Section"
              value={form.section}
              onChange={handleChange}
            />
          </div>

          <button
            onClick={signup}
            className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 transition font-semibold"
          >
            Sign Up
          </button>
        </div>

        <p className="text-center text-zinc-400 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
