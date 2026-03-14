import { Link } from "react-router-dom";
import FollowButton from "./FollowButton";

export default function NoteCard({
  note,
  likeCount = 0,
  hasAccess = false,
  ribbon = null,
  onLike,
  onBookmark,
  onBuy,
  onDownload,
  isDownloading = false,
  allowDownload = true,
  isBuying = false,
  isBookmarked = false,
  isBookmarking = false,
  isLiked = false,
  isLiking = false,
}) {
  const noteHasAccess = note.has_access || hasAccess;
  const locked = note.is_paid && !noteHasAccess;

  return (
    <div className="minimal-card group relative p-6 dark:bg-zinc-900 dark:border-zinc-700">
      {ribbon && (
        <div className="absolute -left-3 -top-3 z-30">
          <span className="inline-flex items-center border border-white bg-black px-3 py-1 text-xs font-black uppercase tracking-wider text-white shadow-md">
            {ribbon}
          </span>
        </div>
      )}

      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className="line-clamp-2 text-xl font-bold text-black dark:text-white transition-all group-hover:underline group-hover:decoration-2 group-hover:underline-offset-4">
            {note.title}
          </h3>
          <p className="mt-1 text-sm font-medium uppercase tracking-wide text-gray-500 dark:text-zinc-400">
            {note.subject} {note.unit ? `• Unit ${note.unit}` : ""}
          </p>
        </div>

        {note.is_paid ? (
          <span className="inline-flex items-center border border-black dark:border-zinc-500 bg-black dark:bg-zinc-800 px-3 py-1 text-xs font-bold text-white">
            INR {note.price}
          </span>
        ) : (
          <span className="inline-flex items-center border border-black dark:border-zinc-500 bg-white dark:bg-zinc-800 px-3 py-1 text-xs font-bold text-black dark:text-white">
            FREE
          </span>
        )}
      </div>

      <div className="mb-3 flex flex-wrap gap-2 text-xs font-bold uppercase tracking-wide text-gray-400 dark:text-zinc-500">
        <span>Sem {note.semester}</span>
        <span>•</span>
        <span>{note.dept}</span>
        {note.college_name && (
          <>
            <span>•</span>
            <span className="text-gray-600 dark:text-zinc-400">{note.college_name}</span>
          </>
        )}
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {note.status === "approved" && (
          <span className="inline-flex items-center border border-green-700 bg-green-50 dark:bg-green-900/20 dark:border-green-700/50 px-2 py-0.5 text-xs font-bold uppercase text-green-700 dark:text-green-400">
            Approved
          </span>
        )}

        {note.verified_seller && (
          <span className="inline-flex items-center border border-sky-700 bg-sky-50 dark:bg-sky-900/20 dark:border-sky-700/50 px-2 py-0.5 text-xs font-bold uppercase text-sky-700 dark:text-sky-400">
            Verified Seller
          </span>
        )}

        {note.views > 100 && (
          <span className="inline-flex items-center border border-amber-700 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-700/50 px-2 py-0.5 text-xs font-bold uppercase text-amber-700 dark:text-amber-400">
            Popular
          </span>
        )}

        {locked && (
          <span className="inline-flex items-center border border-red-700 bg-red-50 dark:bg-red-900/20 dark:border-red-700/50 px-2 py-0.5 text-xs font-bold uppercase text-red-700 dark:text-red-400">
            Locked
          </span>
        )}

        {note.is_paid && hasAccess && (
          <span className="inline-flex items-center border border-blue-700 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-700/50 px-2 py-0.5 text-xs font-bold uppercase text-blue-700 dark:text-blue-400">
            Purchased
          </span>
        )}
      </div>

      {note.uploader_name && (
        <div className="mb-4 flex items-center gap-3 border-b border-gray-100 dark:border-zinc-700 pb-3">
          <div className="flex-1">
            <p className="text-xs font-bold uppercase tracking-wide text-gray-400 dark:text-zinc-500">Uploaded by</p>
            <div className="flex items-center gap-2">
              <p className="text-sm font-bold text-black dark:text-white">{note.uploader_name}</p>
              {note.seller_trust_level === "top" && (
                <span className="inline-flex items-center border border-yellow-700 bg-yellow-50 dark:bg-yellow-900/20 px-2 py-0.5 text-xs font-bold uppercase text-yellow-700 dark:text-yellow-400">
                  Top
                </span>
              )}
              {note.seller_trust_level === "trusted" && (
                <span className="inline-flex items-center border border-blue-700 bg-blue-50 dark:bg-blue-900/20 px-2 py-0.5 text-xs font-bold uppercase text-blue-700 dark:text-blue-400">
                  Trusted
                </span>
              )}
              {note.seller_trust_level === "new" && (
                <span className="inline-flex items-center border border-gray-400 dark:border-zinc-600 bg-gray-50 dark:bg-zinc-800 px-2 py-0.5 text-xs font-bold uppercase text-gray-600 dark:text-zinc-400">
                  New
                </span>
              )}
            </div>
          </div>
          {note.avg_rating > 0 && (
            <div className="text-right">
              <p className="text-xs font-bold uppercase tracking-wide text-gray-400 dark:text-zinc-500">Rating</p>
              <p className="text-sm font-bold text-black dark:text-white">
                {note.avg_rating.toFixed(1)} <span className="text-gray-400 dark:text-zinc-500">({note.review_count})</span>
              </p>
            </div>
          )}
        </div>
      )}

      <p className="mb-6 line-clamp-2 text-sm leading-relaxed text-gray-600 dark:text-zinc-400">
        {note.description || "No description available"}
      </p>

      <div className="mb-6 flex items-center justify-between border-t border-gray-100 dark:border-zinc-700 pt-4 text-sm font-bold text-gray-500 dark:text-zinc-500">
        <div className="flex items-center gap-4">
          <span>{note.views || 0} views</span>
          <span>{likeCount} likes</span>
        </div>
        {note.uploader_id && <FollowButton creatorId={note.uploader_id} />}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {hasAccess && !note.is_paid && allowDownload && (
          <button
            onClick={onDownload}
            disabled={isDownloading}
            className={`col-span-2 border border-black dark:border-zinc-500 px-4 py-2 text-sm font-bold uppercase tracking-wide transition-smooth btn-ripple ${
              isDownloading
                ? "cursor-not-allowed bg-gray-100 dark:bg-zinc-800 text-gray-400 dark:text-zinc-500"
                : "bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-zinc-200 hover:-translate-y-0.5 hover:shadow-lg"
            }`}
          >
            {isDownloading ? "Downloading..." : "Download"}
          </button>
        )}

        {!hasAccess && onBuy && (
          <button
            onClick={onBuy}
            disabled={isBuying}
            className={`col-span-2 border border-black dark:border-zinc-500 px-4 py-2 text-sm font-bold uppercase tracking-wide transition-smooth btn-ripple ${
              isBuying
                ? "cursor-not-allowed bg-gray-100 dark:bg-zinc-800 text-gray-400 dark:text-zinc-500"
                : "bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-zinc-200 hover:-translate-y-0.5 hover:shadow-lg"
            }`}
          >
            {isBuying ? "Processing..." : note.is_paid ? `Buy Now • INR ${note.price}` : "Get For Free"}
          </button>
        )}

        {hasAccess && (
          <Link
            to={`/secure-viewer/${note.id}`}
            className="col-span-2 border border-black dark:border-zinc-500 bg-white dark:bg-zinc-800 px-4 py-2 text-center text-sm font-bold uppercase tracking-wide text-black dark:text-white transition-smooth hover:bg-gray-50 dark:hover:bg-zinc-700 hover:-translate-y-0.5 hover:shadow-md"
          >
            Read Note
          </Link>
        )}

        <Link
          to={`/notes/${note.id}`}
          className="col-span-1 border border-gray-200 dark:border-zinc-700 px-3 py-2 text-center text-xs font-bold uppercase tracking-wide text-gray-600 dark:text-zinc-400 transition-all hover:border-black dark:hover:border-zinc-400 hover:text-black dark:hover:text-white"
        >
          Details
        </Link>

        <div className="col-span-1 flex gap-2">
          <button
            onClick={onLike}
            disabled={isLiking}
            className={`flex flex-1 items-center justify-center border text-xs font-bold uppercase transition-all ${
              isLiking
                ? "border-gray-100 dark:border-zinc-700 text-gray-300 dark:text-zinc-600"
                : isLiked
                ? "border-black dark:border-white bg-black dark:bg-white text-white dark:text-black"
                : "border-gray-200 dark:border-zinc-700 text-gray-400 dark:text-zinc-500 hover:border-black dark:hover:border-zinc-400 hover:text-black dark:hover:text-white"
            }`}
          >
            {isLiked ? "Liked" : "Like"}
          </button>

          <button
            onClick={onBookmark}
            disabled={isBookmarking}
            className={`flex flex-1 items-center justify-center border text-xs font-bold uppercase transition-all ${
              isBookmarking
                ? "border-gray-100 dark:border-zinc-700 text-gray-300 dark:text-zinc-600"
                : isBookmarked
                ? "border-black dark:border-white bg-black dark:bg-white text-white dark:text-black"
                : "border-gray-200 dark:border-zinc-700 text-gray-400 dark:text-zinc-500 hover:border-black dark:hover:border-zinc-400 hover:text-black dark:hover:text-white"
            }`}
          >
            {isBookmarked ? "Saved" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
