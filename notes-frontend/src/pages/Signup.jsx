import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/axios";
import toast from "react-hot-toast";

export default function Signup() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    dept: "CSE",
    year: 3,
    section: "G1",
  });

  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: name === "year" ? parseInt(value, 10) || p.year : value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/signup", form);
      toast.success("Account created! Please login.");
      navigate("/login");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4 font-sans text-black page-enter">
      <div className="w-full max-w-md fade-in-up">
        {/* Logo/Brand */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-black mb-6 scale-in">
            <span className="text-white font-bold text-3xl">N</span>
          </div>
          <h1 className="text-4xl font-black uppercase tracking-tighter mb-2">
            Notes Market
          </h1>
          <p className="text-gray-500 uppercase tracking-wide text-sm font-bold">Join the platform</p>
        </div>

        {/* Signup Form */}
        <div className="bg-white p-0">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Name */}
            <div className="fade-in stagger-1">
              <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
                Full Name
              </label>
              <input
                type="text"
                name="name"
                value={form.name}
                onChange={handleChange}
                required
                className="input-field rounded-none border-black focus:ring-black"
                placeholder="Enter your full name"
              />
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
                Email Address
              </label>
              <input
                type="email"
                name="email"
                value={form.email}
                onChange={handleChange}
                required
                className="input-field rounded-none border-black focus:ring-black"
                placeholder="you@example.com"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
                Password
              </label>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                required
                minLength={6}
                className="input-field rounded-none border-black focus:ring-black"
                placeholder="••••••••"
              />
            </div>

            {/* Academic Info */}
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
                  Dept
                </label>
                <select
                  name="dept"
                  value={form.dept}
                  onChange={handleChange}
                  className="input-field rounded-none border-black focus:ring-black"
                >
                  <option value="CSE">CSE</option>
                  <option value="ECE">ECE</option>
                  <option value="EEE">EEE</option>
                  <option value="MECH">MECH</option>
                  <option value="CIVIL">CIVIL</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
                  Year
                </label>
                <select
                  name="year"
                  value={form.year}
                  onChange={handleChange}
                  className="input-field rounded-none border-black focus:ring-black"
                >
                  <option value={1}>1st</option>
                  <option value={2}>2nd</option>
                  <option value={3}>3rd</option>
                  <option value={4}>4th</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">
                  Section
                </label>
                <input
                  type="text"
                  name="section"
                  value={form.section}
                  onChange={handleChange}
                  className="input-field rounded-none border-black focus:ring-black"
                  placeholder="G1"
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full rounded-none h-12 text-sm font-bold tracking-widest hover:bg-gray-900 border border-transparent btn-ripple fade-in stagger-4"
            >
              {loading ? "creating account..." : "create account"}
            </button>
          </form>

          {/* Login Link */}
          <div className="mt-8 text-center border-t border-gray-100 pt-8">
            <p className="text-gray-500 text-sm">
              Already have an account?{" "}
              <Link
                to="/login"
                className="font-bold text-black border-b-2 border-black hover:bg-black hover:text-white transition-all pb-0.5"
              >
                Sign in here
              </Link>
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-gray-400 text-xs uppercase tracking-widest">
            By signing up, you agree to our Terms
          </p>
        </div>
      </div>
    </div>
  );
}
