import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../context/useTheme";
import toast from "react-hot-toast";
import { useEffect, useMemo, useRef, useState } from "react";
import { Sun, Moon } from "lucide-react";

export default function Layout({ title, children }) {
  const { user, logout } = useAuth();
  const { theme, toggle: toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  const [openGroup, setOpenGroup] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const profileRef = useRef(null);
  const navRef = useRef(null);

  const isActive = (path) => location.pathname === path;
  const hasAnyActive = (links) => links.some((link) => isActive(link.to));

  const primaryLinks = useMemo(
    () => [
      { to: "/dashboard", label: "Dashboard" },
      { to: "/trending", label: "Trending" },
      { to: "/upload-note", label: "Upload" },
      { to: "/my-purchases", label: "Purchases" },
      { to: "/notifications", label: "Alerts" },
    ],
    [],
  );

  const groupedLinks = useMemo(
    () => [
      {
        key: "library",
        label: "Library",
        links: [
          { to: "/my-uploads", label: "My Uploads" },
          { to: "/my-library", label: "My Library" },
          { to: "/my-bookmarks", label: "Bookmarks" },
          { to: "/wallet", label: "Wallet" },
        ],
      },
      {
        key: "sell",
        label: "Sell",
        links: [
          { to: "/seller-dashboard", label: "Seller Dashboard" },
          { to: "/seller-guidelines", label: "Seller Guidelines" },
          { to: "/passes", label: "Creator Passes" },
          { to: "/requests", label: "Requests" },
          { to: "/bundles", label: "Bundles" },
          { to: "/monetization", label: "Monetization" },
        ],
      },
      {
        key: "community",
        label: "Community",
        links: [
          { to: "/spaces", label: "Class Spaces" },
          { to: "/top-creators", label: "Top Creators" },
          { to: "/following", label: "Following" },
          { to: "/leaderboard", label: "Leaderboard" },
        ],
      },
    ],
    [],
  );

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setShowProfileDropdown(false);
      }
      if (navRef.current && !navRef.current.contains(event.target)) {
        setOpenGroup(null);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    toast.success("Logged out successfully");
    navigate("/login", { replace: true });
  };

  const handleProfileClick = () => {
    navigate("/profile");
    setShowProfileDropdown(false);
  };

  const handleNavNavigate = () => {
    setOpenGroup(null);
    setMobileOpen(false);
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <header className="sticky top-0 z-50 border-b border-black/20 dark:border-zinc-700 bg-white/90 dark:bg-zinc-900/90 backdrop-blur fade-in-down">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-3">
            <div className="flex h-8 w-8 items-center justify-center border border-black dark:border-white bg-black dark:bg-white">
              <span className="text-sm font-bold text-white dark:text-black">N</span>
            </div>
            <h1 className="text-xl font-black uppercase tracking-[0.14em] text-black dark:text-white">Notes Market</h1>
          </div>

          <div className="flex items-center space-x-3">
            {/* Dark mode toggle */}
            <button
              onClick={toggleTheme}
              aria-label="Toggle dark mode"
              className="flex h-9 w-9 items-center justify-center border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 text-black dark:text-white transition-colors hover:bg-zinc-100 dark:hover:bg-zinc-700 focus:outline-none"
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? (
                <Sun size={16} strokeWidth={2.5} />
              ) : (
                <Moon size={16} strokeWidth={2.5} />
              )}
            </button>

            {user && (
              <>
                <div className="hidden text-right sm:block">
                  <p className="text-sm font-bold uppercase text-black dark:text-white">{user.name}</p>
                  <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-zinc-400">{user.role}</p>
                  {!user.is_email_verified && <p className="mt-1 text-xs font-medium text-red-500">Not Verified</p>}
                </div>

                <div className="relative" ref={profileRef}>
                  <button
                    onClick={() => setShowProfileDropdown((prev) => !prev)}
                    className="flex h-10 w-10 items-center justify-center border border-black dark:border-zinc-500 bg-white dark:bg-zinc-800 font-bold text-black dark:text-white transition-colors duration-200 hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black focus:outline-none"
                  >
                    <span>{user.name.charAt(0).toUpperCase()}</span>
                  </button>

                  {showProfileDropdown && (
                    <div className="absolute right-0 z-50 mt-2 w-48 border border-black dark:border-zinc-600 bg-white dark:bg-zinc-800 shadow-[8px_8px_0px_0px_rgba(0,0,0,0.08)]">
                      <div className="border-b border-gray-200 dark:border-zinc-700 p-3">
                        <p className="text-sm font-bold uppercase text-black dark:text-white">{user.name}</p>
                        <p className="text-xs uppercase text-gray-500 dark:text-zinc-400">{user.role}</p>
                      </div>

                      <div className="py-1">
                        <button
                          onClick={handleProfileClick}
                          className="w-full px-4 py-2 text-left text-sm uppercase tracking-wide text-black dark:text-zinc-100 transition-colors hover:bg-black hover:text-white dark:hover:bg-zinc-700"
                        >
                          My Profile
                        </button>

                        {!user.is_email_verified && (
                          <Link
                            to="/verify-email"
                            onClick={() => setShowProfileDropdown(false)}
                            className="block px-4 py-2 text-sm uppercase tracking-wide text-red-600 transition-colors hover:bg-red-50 dark:hover:bg-red-900/20"
                          >
                            Verify Email
                          </Link>
                        )}

                        <button
                          onClick={handleLogout}
                          className="w-full px-4 py-2 text-left text-sm uppercase tracking-wide text-black dark:text-zinc-100 transition-colors hover:bg-black hover:text-white dark:hover:bg-zinc-700"
                        >
                          Logout
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {user && (
        <nav className="border-b border-gray-200 dark:border-zinc-700 bg-white/90 dark:bg-zinc-900/90 backdrop-blur">
          <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8" ref={navRef}>
            <div className="flex items-center justify-between gap-3 lg:hidden">
              <div className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500 dark:text-zinc-400">Navigation</div>
              <button
                onClick={() => setMobileOpen((prev) => !prev)}
                className="border border-black dark:border-zinc-500 px-3 py-2 text-xs font-bold uppercase tracking-wide text-black dark:text-white transition-colors hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black"
              >
                {mobileOpen ? "Close" : "Menu"}
              </button>
            </div>

            <div className="hidden items-center gap-2 lg:flex">
              {primaryLinks.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  onClick={handleNavNavigate}
                  className={`whitespace-nowrap border px-3 py-2 text-xs font-bold uppercase tracking-wide transition-all duration-200 ${isActive(link.to)
                    ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                    : "border-transparent text-gray-600 dark:text-zinc-400 hover:border-black hover:text-black dark:hover:border-zinc-400 dark:hover:text-white"
                    }`}
                >
                  {link.label}
                </Link>
              ))}

              {groupedLinks.map((group) => (
                <div key={group.key} className="relative">
                  <button
                    onClick={() => setOpenGroup((prev) => (prev === group.key ? null : group.key))}
                    className={`whitespace-nowrap border px-3 py-2 text-xs font-bold uppercase tracking-wide transition-all duration-200 ${hasAnyActive(group.links) || openGroup === group.key
                      ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                      : "border-transparent text-gray-600 dark:text-zinc-400 hover:border-black hover:text-black dark:hover:border-zinc-400 dark:hover:text-white"
                      }`}
                  >
                    {group.label}
                  </button>
                  {openGroup === group.key && (
                    <div className="absolute left-0 top-full z-40 mt-2 min-w-52 border border-black dark:border-zinc-600 bg-white dark:bg-zinc-800 shadow-[8px_8px_0px_0px_rgba(0,0,0,0.08)]">
                      {group.links.map((link) => (
                        <Link
                          key={link.to}
                          to={link.to}
                          onClick={handleNavNavigate}
                          className={`block border-b border-gray-100 dark:border-zinc-700 px-4 py-3 text-xs font-bold uppercase tracking-wide transition-colors last:border-b-0 ${isActive(link.to)
                            ? "bg-black text-white dark:bg-white dark:text-black"
                            : "text-gray-700 dark:text-zinc-300 hover:bg-black hover:text-white dark:hover:bg-zinc-700 dark:hover:text-white"
                            }`}
                        >
                          {link.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {(user.role === "admin" || user.role === "moderator") && (
                <>
                  <Link
                    to="/moderation-dashboard"
                    onClick={handleNavNavigate}
                    className={`whitespace-nowrap border px-3 py-2 text-xs font-bold uppercase tracking-wide transition-all duration-200 ${isActive("/moderation-dashboard")
                      ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                      : "border-transparent text-gray-700 dark:text-zinc-400 hover:border-black hover:text-black dark:hover:border-zinc-400 dark:hover:text-white"
                      }`}
                  >
                    Moderation
                  </Link>
                  <Link
                    to="/ops-dashboard"
                    onClick={handleNavNavigate}
                    className={`whitespace-nowrap border px-3 py-2 text-xs font-bold uppercase tracking-wide transition-all duration-200 ${isActive("/ops-dashboard")
                      ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                      : "border-transparent text-gray-700 dark:text-zinc-400 hover:border-black hover:text-black dark:hover:border-zinc-400 dark:hover:text-white"
                      }`}
                  >
                    Ops
                  </Link>
                  {user.role === "admin" && (
                    <>
                      <Link
                        to="/admin-analytics"
                        onClick={handleNavNavigate}
                        className={`whitespace-nowrap border px-3 py-2 text-xs font-bold uppercase tracking-wide transition-all duration-200 ${isActive("/admin-analytics")
                          ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                          : "border-transparent text-gray-700 dark:text-zinc-400 hover:border-black hover:text-black dark:hover:border-zinc-400 dark:hover:text-white"
                          }`}
                      >
                        Analytics
                      </Link>
                      <Link
                        to="/admin-domain-candidates"
                        onClick={handleNavNavigate}
                        className={`whitespace-nowrap border px-3 py-2 text-xs font-bold uppercase tracking-wide transition-all duration-200 ${isActive("/admin-domain-candidates")
                          ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                          : "border-transparent text-gray-700 dark:text-zinc-400 hover:border-black hover:text-black dark:hover:border-zinc-400 dark:hover:text-white"
                          }`}
                      >
                        Domains
                      </Link>
                    </>
                  )}
                </>
              )}
            </div>

            {mobileOpen && (
              <div className="mt-3 space-y-3 border border-gray-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-3 lg:hidden slide-in-left">
                <div className="grid gap-2">
                  {primaryLinks.map((link) => (
                    <Link
                      key={link.to}
                      to={link.to}
                      onClick={handleNavNavigate}
                      className={`border px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors ${isActive(link.to)
                        ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                        : "border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-zinc-300 hover:border-black hover:bg-black hover:text-white dark:hover:border-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-white"
                        }`}
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>

                {groupedLinks.map((group) => (
                  <div key={group.key} className="border border-gray-200 dark:border-zinc-700">
                    <div className="border-b border-gray-200 dark:border-zinc-700 px-3 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-gray-500 dark:text-zinc-400">
                      {group.label}
                    </div>
                    <div className="grid">
                      {group.links.map((link) => (
                        <Link
                          key={link.to}
                          to={link.to}
                          onClick={handleNavNavigate}
                          className={`border-b border-gray-100 dark:border-zinc-700 px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors last:border-b-0 ${isActive(link.to)
                            ? "bg-black text-white dark:bg-white dark:text-black"
                            : "text-gray-700 dark:text-zinc-300 hover:bg-black hover:text-white dark:hover:bg-zinc-700 dark:hover:text-white"
                            }`}
                        >
                          {link.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}

                {(user.role === "admin" || user.role === "moderator") && (
                  <>
                    <Link
                      to="/moderation-dashboard"
                      onClick={handleNavNavigate}
                      className={`block border px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors ${isActive("/moderation-dashboard")
                        ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                        : "border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-zinc-300 hover:border-black hover:bg-black hover:text-white dark:hover:bg-zinc-700 dark:hover:text-white"
                        }`}
                    >
                      Moderation
                    </Link>
                    <Link
                      to="/ops-dashboard"
                      onClick={handleNavNavigate}
                      className={`block border px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors ${isActive("/ops-dashboard")
                        ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                        : "border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-zinc-300 hover:border-black hover:bg-black hover:text-white dark:hover:bg-zinc-700 dark:hover:text-white"
                        }`}
                    >
                      Ops
                    </Link>
                    {user.role === "admin" && (
                      <>
                        <Link
                          to="/admin-analytics"
                          onClick={handleNavNavigate}
                          className={`block border px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors ${isActive("/admin-analytics")
                            ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                            : "border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-zinc-300 hover:border-black hover:bg-black hover:text-white dark:hover:bg-zinc-700 dark:hover:text-white"
                            }`}
                        >
                          Analytics
                        </Link>
                        <Link
                          to="/admin-domain-candidates"
                          onClick={handleNavNavigate}
                          className={`block border px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors ${isActive("/admin-domain-candidates")
                            ? "border-black bg-black text-white dark:border-white dark:bg-white dark:text-black"
                            : "border-gray-200 dark:border-zinc-700 text-gray-700 dark:text-zinc-300 hover:border-black hover:bg-black hover:text-white dark:hover:bg-zinc-700 dark:hover:text-white"
                            }`}
                        >
                          Domains
                        </Link>
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </nav>
      )}

      {/* Unverified email banner */}
      {user && !user.is_email_verified && (
        <div className="border-b border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-900/20 px-4 py-2.5">
          <div className="mx-auto max-w-7xl flex items-center justify-between gap-4 sm:px-6 lg:px-8">
            <p className="text-xs font-bold uppercase tracking-wide text-amber-800 dark:text-amber-300">
              Verify your college email to upload notes and access all features.
            </p>
            <Link
              to="/verify-email"
              className="shrink-0 border border-amber-600 dark:border-amber-500 bg-amber-600 dark:bg-amber-700 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-white hover:bg-amber-700 transition-colors"
            >
              Verify Now
            </Link>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        {title && (
          <div className="mb-12 border-b border-black dark:border-zinc-600 pb-4">
            <h1 className="text-4xl font-black uppercase tracking-tight text-black dark:text-white">{title}</h1>
          </div>
        )}

        {children}
      </main>
    </div>
  );
}
