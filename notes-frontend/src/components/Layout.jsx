import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Layout({ title, children }) {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="max-w-5xl mx-auto px-4 py-6">
        {/* Top Bar */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
            {user && (
              <p className="text-zinc-400 mt-1">
                Logged in as <span className="text-zinc-200 font-medium">{user.name}</span>{" "}
                <span className="text-zinc-500">({user.role})</span>
              </p>
            )}
          </div>

          {user && (
            <button
              onClick={logout}
              className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
            >
              Logout
            </button>
          )}
        </div>

        {/* Nav */}
        {user && (
          <div className="flex flex-wrap gap-3 mb-8">
            <Link className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition" to="/dashboard">
              Dashboard
            </Link>
            <Link className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition" to="/upload">
              Upload Note
            </Link>
            <Link className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition" to="/leaderboard">
              Leaderboard
            </Link>
            <Link className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition" to="/my-uploads">
              My Uploads
            </Link>
            <Link className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition" to="/my-bookmarks">
              My Bookmarks
            </Link>
            <Link className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition" to="/my-purchases">
              My Purchases
            </Link>
            <Link className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition" to="/trending">
              Trending
            </Link>
            <Link className="px-4 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 transition" to="/seller-dashboard">
              Seller Dashboard
            </Link>

            {(user.role === "admin" || user.role === "moderator") && (
              <Link className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition" to="/moderation">
                Moderation
              </Link>
            )}
          </div>
        )}

        {/* Page Content */}
        <div>{children}</div>
      </div>
    </div>
  );
}
