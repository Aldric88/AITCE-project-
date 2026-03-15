import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";
import { useNavigate, useLocation } from "react-router-dom";

const RESEND_COOLDOWN = 60; // seconds — must match backend

export default function VerifyEmail() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const emailToUse = user?.email || location.state?.email;

  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [devOtp, setDevOtp] = useState(null); // only populated when SMTP not configured
  const [cooldown, setCooldown] = useState(0); // seconds remaining before resend allowed
  const [attemptsLeft, setAttemptsLeft] = useState(3);

  // Redirect if already verified
  useEffect(() => {
    if (user?.is_email_verified) {
      navigate("/dashboard", { replace: true });
    }
  }, [user, navigate]);

  // Countdown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => Math.max(0, c - 1)), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const sendOtp = async () => {
    try {
      setLoading(true);
      const res = await api.post("/verify/send-otp", { email: emailToUse });
      setOtpSent(true);
      setCooldown(RESEND_COOLDOWN);
      setAttemptsLeft(3);
      setOtp("");
      if (res.data.otp) {
        setDevOtp(res.data.otp);
        toast.success(`Dev mode — OTP: ${res.data.otp}`);
      } else {
        setDevOtp(null);
        toast.success("OTP sent to your college email!");
      }
    } catch (err) {
      const detail = err.response?.data?.detail || "Failed to send OTP";
      // Extract remaining seconds from rate-limit message
      const match = detail.match(/(\d+) second/);
      if (match) setCooldown(parseInt(match[1]));
      toast.error(detail);
    } finally {
      setLoading(false);
    }
  };

  const confirmOtp = async () => {
    if (otp.length !== 6) return;
    try {
      setLoading(true);
      await api.post("/verify/confirm-otp", { email: emailToUse, otp });
      toast.success("Email verified! Welcome to Notes Market.");
      await refreshUser();
    } catch (err) {
      const detail = err.response?.data?.detail || "OTP verification failed";
      toast.error(detail);
      // Parse remaining attempts from response
      const match = detail.match(/(\d+) attempt/);
      if (match) setAttemptsLeft(parseInt(match[1]));
      // OTP invalidated — reset to send step
      if (detail.includes("Too many") || detail.includes("expired")) {
        setOtpSent(false);
        setOtp("");
        setDevOtp(null);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Verify Email">
      <div className="mx-auto max-w-lg">
        <div className="border border-black dark:border-zinc-600 bg-white dark:bg-zinc-900">
          {/* Header */}
          <div className="border-b border-black dark:border-zinc-600 bg-black dark:bg-white p-6">
            <h2 className="text-2xl font-black uppercase tracking-tight text-white dark:text-black">
              College Email Verification
            </h2>
            <p className="mt-1 text-xs font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-600">
              Required to upload notes and access all features
            </p>
          </div>

          <div className="p-8">
            {/* Email display */}
            <div className="mb-6 border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800 p-4">
              <p className="text-[10px] font-black uppercase tracking-widest text-zinc-500 dark:text-zinc-400 mb-1">
                College Email
              </p>
              <p className="text-sm font-bold text-black dark:text-white">{emailToUse}</p>
            </div>

            {/* Steps */}
            <div className="mb-8 flex gap-0">
              {["Send OTP", "Enter Code", "Verified"].map((step, i) => {
                const active = i === 0 ? !otpSent : i === 1 ? otpSent : false;
                const done = i === 0 ? otpSent : false;
                return (
                  <div key={step} className="flex-1">
                    <div
                      className={`border-t-4 pt-2 text-[10px] font-black uppercase tracking-wider ${
                        done
                          ? "border-black dark:border-white text-zinc-400"
                          : active
                          ? "border-black dark:border-white text-black dark:text-white"
                          : "border-zinc-200 dark:border-zinc-700 text-zinc-300 dark:text-zinc-600"
                      }`}
                    >
                      {step}
                    </div>
                  </div>
                );
              })}
            </div>

            {!otpSent ? (
              /* ── Step 1: Send OTP ── */
              <div className="space-y-4">
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  We'll send a 6-digit verification code to your college email.
                  The code is valid for <strong>10 minutes</strong>.
                </p>

                <button
                  onClick={sendOtp}
                  disabled={loading || cooldown > 0}
                  className="btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? "Sending..." : cooldown > 0 ? `Resend in ${cooldown}s` : "Send Verification Code"}
                </button>
              </div>
            ) : (
              /* ── Step 2: Enter OTP ── */
              <div className="space-y-5">
                <div>
                  <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-4">
                    Enter the 6-digit code sent to your college email.
                  </p>

                  {/* Dev mode OTP hint */}
                  {devOtp && (
                    <div className="mb-4 border border-amber-300 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700 p-3">
                      <p className="text-[10px] font-black uppercase tracking-wider text-amber-700 dark:text-amber-400 mb-1">
                        Dev Mode — SMTP not configured
                      </p>
                      <p className="text-lg font-black font-mono tracking-[0.3em] text-amber-800 dark:text-amber-300">
                        {devOtp}
                      </p>
                    </div>
                  )}

                  <label className="block text-[10px] font-black uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2">
                    Verification Code
                  </label>
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    className="w-full border border-black dark:border-zinc-500 bg-white dark:bg-zinc-800 px-4 py-4 text-center text-3xl font-black font-mono tracking-[0.5em] text-black dark:text-white focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white"
                    placeholder="000000"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                  />
                </div>

                {/* Attempt counter */}
                {attemptsLeft < 3 && (
                  <div className="border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-3">
                    <p className="text-xs font-bold uppercase tracking-wide text-red-600 dark:text-red-400">
                      {attemptsLeft} attempt{attemptsLeft !== 1 ? "s" : ""} remaining before OTP is invalidated
                    </p>
                  </div>
                )}

                <button
                  onClick={confirmOtp}
                  disabled={loading || otp.length !== 6}
                  className="btn-primary w-full py-3 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? "Verifying..." : "Verify Code"}
                </button>

                {/* Resend */}
                <div className="flex items-center justify-between border-t border-zinc-100 dark:border-zinc-800 pt-4">
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">
                    Didn't receive the code?
                  </p>
                  <button
                    onClick={sendOtp}
                    disabled={loading || cooldown > 0}
                    className="text-xs font-black uppercase tracking-wide text-black dark:text-white underline disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {cooldown > 0 ? `Resend in ${cooldown}s` : "Resend OTP"}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Footer note */}
          <div className="border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 px-8 py-4">
            <p className="text-[11px] font-medium text-zinc-500 dark:text-zinc-400">
              Only college/university email addresses are accepted.
              Personal emails (Gmail, Yahoo, etc.) cannot be used on Notes Market.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}
