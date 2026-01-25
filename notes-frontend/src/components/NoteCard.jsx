import { Link } from "react-router-dom";

export default function NoteCard({
  note,
  likeCount = 0,

  hasAccess = true,

  // actions
  onLike,
  onBookmark,
  onBuy,
  onDownload,

  // ui states
  isDownloading = false,
  allowDownload = true,

  isBuying = false,            // NEW
  isBookmarked = false,        // NEW
  isBookmarking = false,       // NEW
  isLiked = false,             // NEW
  isLiking = false,            // NEW
}) {
  const locked = note.is_paid && !hasAccess;

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 shadow">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-xl font-semibold">{note.title}</h3>

        {/* FREE / PAID badge */}
        {note.is_paid ? (
          <span className="text-xs px-3 py-1 rounded-full bg-yellow-600/30 text-yellow-200 border border-yellow-500/30">
            PAID ₹{note.price}
          </span>
        ) : (
          <span className="text-xs px-3 py-1 rounded-full bg-emerald-600/20 text-emerald-200 border border-emerald-500/30">
            FREE
          </span>
        )}
      </div>

      <p className="text-zinc-400 mt-2">
        {note.subject} • Unit {note.unit} • Sem {note.semester} • {note.dept}
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <span className="text-sm px-3 py-1 rounded-full bg-zinc-800 text-zinc-200">
          Status: {note.status}
        </span>

        {locked && (
          <span className="text-sm px-3 py-1 rounded-full bg-red-600/20 text-red-200 border border-red-500/30">
            Locked 🔒
          </span>
        )}

        {note.is_paid && hasAccess && (
          <span className="text-sm px-3 py-1 rounded-full bg-indigo-600/20 text-indigo-200 border border-indigo-500/30">
            Purchased ✅
          </span>
        )}

        {isBookmarked && (
          <span className="text-sm px-3 py-1 rounded-full bg-emerald-600/20 text-emerald-200 border border-emerald-500/30">
            Bookmarked ✅
          </span>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        {/* VIEW / BUY logic */}
        {!note.is_paid ? (
          <Link
            to="/viewer"
            state={{ note }}
            className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
          >
            View Note
          </Link>
        ) : hasAccess ? (
          <Link
            to="/viewer"
            state={{ note }}
            className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
          >
            View Note
          </Link>
        ) : (
          <button
            onClick={onBuy}
            disabled={isBuying}
            className={`px-4 py-2 rounded-xl transition font-semibold ${
              isBuying
                ? "bg-yellow-500/40 cursor-not-allowed text-zinc-200"
                : "bg-yellow-500/90 hover:bg-yellow-400 text-zinc-950"
            }`}
          >
            {isBuying ? "Processing..." : `Buy ₹${note.price}`}
          </button>
        )}

        {/* ✅ Download */}
        {allowDownload && hasAccess && (
          <button
            onClick={onDownload}
            disabled={isDownloading}
            className={`px-4 py-2 rounded-xl transition font-medium ${
              isDownloading
                ? "bg-indigo-600/40 cursor-not-allowed"
                : "bg-indigo-600 hover:bg-indigo-500"
            }`}
          >
            {isDownloading ? "Downloading..." : "⬇️ Download"}
          </button>
        )}

        {/* ✅ Details */}
        <Link
          to={`/notes/${note.id}`}
          className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 transition"
        >
          Details
        </Link>

        {/* ✅ Like */}
        <button
          onClick={onLike}
          disabled={isLiking}
          className={`px-4 py-2 rounded-xl transition font-medium ${
            isLiking
              ? "bg-pink-600/30 cursor-not-allowed"
              : "bg-pink-600/80 hover:bg-pink-500"
          }`}
        >
          {isLiking ? "Updating..." : isLiked ? `❤️ Liked (${likeCount})` : `🤍 Like (${likeCount})`}
        </button>

        {/* ✅ Bookmark toggle */}
        <button
          onClick={onBookmark}
          disabled={isBookmarking}
          className={`px-4 py-2 rounded-xl transition font-medium ${
            isBookmarking
              ? "bg-emerald-600/30 cursor-not-allowed"
              : "bg-emerald-600/80 hover:bg-emerald-500"
          }`}
        >
          {isBookmarking
            ? "Updating..."
            : isBookmarked
            ? "✅ Bookmarked"
            : "🔖 Bookmark"}
        </button>
      </div>
    </div>
  );
}
