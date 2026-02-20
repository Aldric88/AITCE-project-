import { useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";

export default function VerifyEmail() {
  const { user, refreshUser } = useAuth();

  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [otpSent, setOtpSent] = useState(false);

  const sendOtp = async () => {
    try {
      setLoading(true);
      const response = await api.post("/verify/send-otp", { email: user.email });
      
      if (response.data.otp) {
        // Development mode - OTP returned in response
        toast.success(`OTP sent ✅ (For testing: ${response.data.otp})`);
      } else {
        toast.success("OTP sent ✅ check your email");
      }
      
      setOtpSent(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const confirmOtp = async () => {
    try {
      setLoading(true);
      await api.post("/verify/confirm-otp", { email: user.email, otp });
      toast.success("Email verified ✅");
      setOtp("");
      setOtpSent(false);
      await refreshUser();
    } catch (err) {
      toast.error(err.response?.data?.detail || "OTP verification failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Verify Email">
      <div className="max-w-lg mx-auto">
        <div className="glass-card p-8">
          <div className="text-center mb-6">
            <div className="text-5xl mb-4">📧</div>
            <h2 className="text-2xl font-bold text-slate-100">Email Verification</h2>
            <p className="text-slate-400 mt-2">
              Verify your email to unlock all features
            </p>
          </div>

          <div className="bg-slate-800/50 rounded-xl p-4 mb-6">
            <p className="text-sm text-slate-400">Email Address</p>
            <p className="text-slate-200 font-medium">{user?.email}</p>
          </div>

          {user?.is_email_verified ? (
            <div className="text-center py-8">
              <div className="text-6xl mb-4">✅</div>
              <h3 className="text-xl font-semibold text-emerald-300 mb-2">
                Email Verified
              </h3>
              <p className="text-slate-400">
                Your email has been successfully verified
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {!otpSent ? (
                <button
                  onClick={sendOtp}
                  disabled={loading}
                  className="btn-primary w-full"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Sending...
                    </span>
                  ) : (
                    "📤 Send OTP"
                  )}
                </button>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Enter 6-digit OTP
                    </label>
                    <input
                      type="text"
                      maxLength={6}
                      className="input-field text-center text-2xl font-mono"
                      placeholder="000000"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                    />
                  </div>

                  <button
                    onClick={confirmOtp}
                    disabled={loading || otp.length !== 6}
                    className="btn-primary w-full bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-600 hover:to-emerald-700 shadow-lg shadow-emerald-500/25"
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        Verifying...
                      </span>
                    ) : (
                      "✅ Verify OTP"
                    )}
                  </button>

                  <button
                    onClick={() => {
                      setOtpSent(false);
                      setOtp("");
                    }}
                    className="btn-secondary w-full"
                  >
                    ← Back to Send OTP
                  </button>
                </>
              )}
            </div>
          )}

          <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
            <p className="text-sm text-blue-300">
              💡 <strong>Note:</strong> Email verification is required to upload notes and access all features.
            </p>
          </div>
        </div>
      </div>
    </Layout>
  );
}
