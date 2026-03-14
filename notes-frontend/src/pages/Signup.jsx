import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/axios";
import toast from "react-hot-toast";

const PERSONAL_DOMAINS = new Set([
  "gmail.com", "yahoo.com", "yahoo.in", "hotmail.com", "outlook.com",
  "live.com", "icloud.com", "me.com", "protonmail.com", "proton.me",
  "rediffmail.com", "ymail.com", "aol.com", "zoho.com",
]);

const ACADEMIC_TLDS = [".ac.in", ".edu", ".edu.in", ".ac.uk", ".edu.au", ".ac.nz"];

function getDomain(email) {
  const parts = email.split("@");
  return parts.length === 2 ? parts[1].toLowerCase() : "";
}

function quickDomainCheck(email) {
  const domain = getDomain(email);
  if (!domain) return null;
  if (PERSONAL_DOMAINS.has(domain)) return { ok: false, msg: "Personal emails are not accepted. Use your college email." };
  for (const tld of ACADEMIC_TLDS) {
    if (domain.endsWith(tld)) return { ok: true, msg: "Academic domain detected ✓" };
  }
  return null; // unknown — will be checked by backend on blur
}

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
  const [domainStatus, setDomainStatus] = useState(null);
  // null = not checked, { ok, msg, checking? } = result
  const debounceRef = useRef(null);
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((p) => ({ ...p, [name]: name === "year" ? parseInt(value, 10) || p.year : value }));

    if (name === "email") {
      setDomainStatus(null);
      clearTimeout(debounceRef.current);
      const quick = quickDomainCheck(value);
      if (quick) {
        setDomainStatus(quick);
        return;
      }
      // Unknown domain → debounce API check
      const domain = getDomain(value);
      if (!domain || !value.includes("@")) return;
      debounceRef.current = setTimeout(async () => {
        setDomainStatus({ checking: true });
        try {
          const res = await api.post("/auth/check-domain", { email: value });
          setDomainStatus({ ok: res.data.allowed, msg: res.data.allowed
            ? `Verified: ${res.data.institution_name || domain}`
            : res.data.reason });
        } catch {
          setDomainStatus(null);
        }
      }, 800);
    }
  };

  useEffect(() => () => clearTimeout(debounceRef.current), []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (domainStatus && !domainStatus.ok && !domainStatus.checking) {
      toast.error("Fix your email address before submitting.");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/signup", form);
      toast.success("Account created! Please verify your college email.");
      navigate("/verify-email");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  const emailBorderClass =
    domainStatus == null
      ? "border-black dark:border-zinc-500"
      : domainStatus.checking
      ? "border-zinc-400 dark:border-zinc-500"
      : domainStatus.ok
      ? "border-emerald-500"
      : "border-red-500";

  return (
    <div className="min-h-screen bg-white dark:bg-zinc-950 flex items-center justify-center px-4 font-sans text-black dark:text-white page-enter">
      <div className="w-full max-w-md fade-in-up">
        {/* Brand */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-black dark:bg-white mb-6 scale-in">
            <span className="text-white dark:text-black font-bold text-3xl">N</span>
          </div>
          <h1 className="text-4xl font-black uppercase tracking-tighter mb-2">Notes Market</h1>
          <p className="text-zinc-500 uppercase tracking-wide text-sm font-bold">Join with your college email</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name */}
          <div className="fade-in stagger-1">
            <label className="block text-xs font-bold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">
              Full Name
            </label>
            <input
              type="text"
              name="name"
              value={form.name}
              onChange={handleChange}
              required
              className="input-field rounded-none border-black dark:border-zinc-500 dark:bg-zinc-800 dark:text-white dark:placeholder-zinc-400 focus:ring-black"
              placeholder="Enter your full name"
            />
          </div>

          {/* Email with live domain validation */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">
              College Email Address
            </label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              required
              className={`input-field rounded-none dark:bg-zinc-800 dark:text-white dark:placeholder-zinc-400 focus:ring-black transition-colors ${emailBorderClass}`}
              placeholder="you@psgtech.ac.in"
            />

            {/* Domain feedback */}
            {domainStatus && (
              <div
                className={`mt-2 flex items-center gap-2 text-xs font-bold uppercase tracking-wide ${
                  domainStatus.checking
                    ? "text-zinc-400"
                    : domainStatus.ok
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {domainStatus.checking ? (
                  <>
                    <span className="inline-block h-3 w-3 animate-spin border-2 border-zinc-400 border-t-transparent rounded-full" />
                    Checking domain...
                  </>
                ) : domainStatus.ok ? (
                  <>✓ {domainStatus.msg}</>
                ) : (
                  <>✗ {domainStatus.msg}</>
                )}
              </div>
            )}

            {/* College email hint */}
            {!domainStatus && (
              <p className="mt-1 text-[11px] text-zinc-400 uppercase tracking-wide">
                Only college/university emails accepted (e.g. .ac.in, .edu)
              </p>
            )}
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">
              Password
            </label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              required
              minLength={6}
              className="input-field rounded-none border-black dark:border-zinc-500 dark:bg-zinc-800 dark:text-white focus:ring-black"
              placeholder="••••••••"
            />
          </div>

          {/* Academic Info */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">Dept</label>
              <select
                name="dept"
                value={form.dept}
                onChange={handleChange}
                className="input-field rounded-none border-black dark:border-zinc-500 dark:bg-zinc-800 dark:text-white focus:ring-black"
              >
                {["CSE", "ECE", "EEE", "MECH", "CIVIL", "IT", "AIML", "DS", "OTHER"].map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">Year</label>
              <select
                name="year"
                value={form.year}
                onChange={handleChange}
                className="input-field rounded-none border-black dark:border-zinc-500 dark:bg-zinc-800 dark:text-white focus:ring-black"
              >
                <option value={1}>1st</option>
                <option value={2}>2nd</option>
                <option value={3}>3rd</option>
                <option value={4}>4th</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wide text-zinc-500 dark:text-zinc-400 mb-2">Section</label>
              <input
                type="text"
                name="section"
                value={form.section}
                onChange={handleChange}
                className="input-field rounded-none border-black dark:border-zinc-500 dark:bg-zinc-800 dark:text-white focus:ring-black"
                placeholder="G1"
              />
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading || (domainStatus && !domainStatus.ok && !domainStatus.checking)}
            className="btn-primary w-full rounded-none h-12 text-sm font-bold tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        {/* Login link */}
        <div className="mt-8 text-center border-t border-zinc-100 dark:border-zinc-800 pt-8">
          <p className="text-zinc-500 text-sm">
            Already have an account?{" "}
            <Link
              to="/login"
              className="font-bold text-black dark:text-white border-b-2 border-black dark:border-white hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-all pb-0.5"
            >
              Sign in here
            </Link>
          </p>
        </div>

        <div className="mt-8 text-center">
          <p className="text-zinc-400 text-xs uppercase tracking-widest">
            College-only platform · By signing up you agree to our Terms
          </p>
        </div>
      </div>
    </div>
  );
}
