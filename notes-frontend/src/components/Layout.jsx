import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";
import { useEffect, useMemo, useRef, useState } from "react";

export default function Layout({ title, children }) {
  const { user, logout } = useAuth();
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
          { to: "/my-bookmarks", label: "Bookmarks" },
        ],
      },
      {
        key: "sell",
        label: "Sell",
        links: [
          { to: "/seller-dashboard", label: "Seller Dashboard" },
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
      <header className="sticky top-0 z-50 border-b border-black/90 bg-white/90 backdrop-blur fade-in-down">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-3">
            <div className="flex h-8 w-8 items-center justify-center border border-black bg-black">
              <span className="text-sm font-bold text-white">N</span>
            </div>
            <h1 className="text-xl font-black uppercase tracking-[0.14em] text-black">Notes Market</h1>
          </div>

          {user && (
            <div className="flex items-center space-x-4">
              <div className="hidden text-right sm:block">
                <p className="text-sm font-bold uppercase text-black">{user.name}</p>
                <p className="text-xs uppercase tracking-wide text-gray-500">{user.role}</p>
                {!user.is_email_verified && <p className="mt-1 text-xs font-medium text-red-600">Not Verified</p>}
              </div>

              <div className="relative" ref={profileRef}>
                <button
                  onClick={() => setShowProfileDropdown((prev) => !prev)}
                  className="flex h-10 w-10 items-center justify-center border border-black bg-white font-bold text-black transition-colors duration-200 hover:bg-black hover:text-white focus:outline-none"
                >
                  <span>{user.name.charAt(0).toUpperCase()}</span>
                </button>

                {showProfileDropdown && (
                  <div className="absolute right-0 z-50 mt-2 w-48 border border-black bg-white shadow-[8px_8px_0px_0px_rgba(0,0,0,0.08)]">
                    <div className="border-b border-gray-200 p-3">
                      <p className="text-sm font-bold uppercase text-black">{user.name}</p>
                      <p className="text-xs uppercase text-gray-500">{user.role}</p>
                    </div>

                    <div className="py-1">
                      <button
                        onClick={handleProfileClick}
                        className="w-full px-4 py-2 text-left text-sm uppercase tracking-wide text-black transition-colors hover:bg-black hover:text-white"
                      >
                        My Profile
                      </button>

                      {!user.is_email_verified && (
                        <Link
                          to="/verify-email"
                          onClick={() => setShowProfileDropdown(false)}
                          className="block px-4 py-2 text-sm uppercase tracking-wide text-red-600 transition-colors hover:bg-red-50"
                        >
                          Verify Email
                        </Link>
                      )}

                      <button
                        onClick={handleLogout}
                        className="w-full px-4 py-2 text-left text-sm uppercase tracking-wide text-black transition-colors hover:bg-black hover:text-white"
                      >
                        Logout
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </header>

      {user && (
        <nav className="border-b border-gray-200 bg-white/90 backdrop-blur">
          <div className="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8" ref={navRef}>
            <div className="flex items-center justify-between gap-3 lg:hidden">
              <div className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500">Navigation</div>
              <button
                onClick={() => setMobileOpen((prev) => !prev)}
                className="border border-black px-3 py-2 text-xs font-bold uppercase tracking-wide text-black transition-colors hover:bg-black hover:text-white"
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
                    ? "border-black bg-black text-white"
                    : "border-transparent text-gray-600 hover:border-black hover:text-black"
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
                      ? "border-black bg-black text-white"
                      : "border-transparent text-gray-600 hover:border-black hover:text-black"
                      }`}
                  >
                    {group.label}
                  </button>
                  {openGroup === group.key && (
                    <div className="absolute left-0 top-full z-40 mt-2 min-w-52 border border-black bg-white shadow-[8px_8px_0px_0px_rgba(0,0,0,0.08)]">
                      {group.links.map((link) => (
                        <Link
                          key={link.to}
                          to={link.to}
                          onClick={handleNavNavigate}
                          className={`block border-b border-gray-100 px-4 py-3 text-xs font-bold uppercase tracking-wide transition-colors last:border-b-0 ${isActive(link.to)
                            ? "bg-black text-white"
                            : "text-gray-700 hover:bg-black hover:text-white"
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
                      ? "border-black bg-black text-white"
                      : "border-transparent text-gray-700 hover:border-black hover:text-black"
                      }`}
                  >
                    Moderation
                  </Link>
                  <Link
                    to="/ops-dashboard"
                    onClick={handleNavNavigate}
                    className={`whitespace-nowrap border px-3 py-2 text-xs font-bold uppercase tracking-wide transition-all duration-200 ${isActive("/ops-dashboard")
                      ? "border-black bg-black text-white"
                      : "border-transparent text-gray-700 hover:border-black hover:text-black"
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
                          ? "border-black bg-black text-white"
                          : "border-transparent text-gray-700 hover:border-black hover:text-black"
                          }`}
                      >
                        Analytics
                      </Link>
                      <Link
                        to="/admin-domain-candidates"
                        onClick={handleNavNavigate}
                        className={`whitespace-nowrap border px-3 py-2 text-xs font-bold uppercase tracking-wide transition-all duration-200 ${isActive("/admin-domain-candidates")
                          ? "border-black bg-black text-white"
                          : "border-transparent text-gray-700 hover:border-black hover:text-black"
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
              <div className="mt-3 space-y-3 border border-gray-200 bg-white p-3 lg:hidden slide-in-left">
                <div className="grid gap-2">
                  {primaryLinks.map((link) => (
                    <Link
                      key={link.to}
                      to={link.to}
                      onClick={handleNavNavigate}
                      className={`border px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors ${isActive(link.to)
                        ? "border-black bg-black text-white"
                        : "border-gray-200 text-gray-700 hover:border-black hover:bg-black hover:text-white"
                        }`}
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>

                {groupedLinks.map((group) => (
                  <div key={group.key} className="border border-gray-200">
                    <div className="border-b border-gray-200 px-3 py-2 text-[11px] font-bold uppercase tracking-[0.18em] text-gray-500">
                      {group.label}
                    </div>
                    <div className="grid">
                      {group.links.map((link) => (
                        <Link
                          key={link.to}
                          to={link.to}
                          onClick={handleNavNavigate}
                          className={`border-b border-gray-100 px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors last:border-b-0 ${isActive(link.to)
                            ? "bg-black text-white"
                            : "text-gray-700 hover:bg-black hover:text-white"
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
                        ? "border-black bg-black text-white"
                        : "border-gray-200 text-gray-700 hover:border-black hover:bg-black hover:text-white"
                        }`}
                    >
                      Moderation
                    </Link>
                    <Link
                      to="/ops-dashboard"
                      onClick={handleNavNavigate}
                      className={`block border px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors ${isActive("/ops-dashboard")
                        ? "border-black bg-black text-white"
                        : "border-gray-200 text-gray-700 hover:border-black hover:bg-black hover:text-white"
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
                            ? "border-black bg-black text-white"
                            : "border-gray-200 text-gray-700 hover:border-black hover:bg-black hover:text-white"
                            }`}
                        >
                          Analytics
                        </Link>
                        <Link
                          to="/admin-domain-candidates"
                          onClick={handleNavNavigate}
                          className={`block border px-3 py-3 text-xs font-bold uppercase tracking-wide transition-colors ${isActive("/admin-domain-candidates")
                            ? "border-black bg-black text-white"
                            : "border-gray-200 text-gray-700 hover:border-black hover:bg-black hover:text-white"
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

      <main className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        {title && (
          <div className="mb-12 border-b border-black pb-4">
            <h1 className="text-4xl font-black uppercase tracking-tight text-black">{title}</h1>
          </div>
        )}

        {children}
      </main>
    </div>
  );
}
