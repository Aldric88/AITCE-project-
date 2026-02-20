import toast from "react-hot-toast";

export function showAiResultToast(data = {}) {
  const ok = !!data.validation_success;
  const title = ok ? "Validation Passed" : "Needs Review";
  const message = data.validation_message || (ok ? "Content validated successfully." : "Validation checks reported issues.");
  const provider = data.provider ? String(data.provider).toUpperCase() : "AI";
  const bucket = data.moderation_bucket ? String(data.moderation_bucket).replaceAll("_", " ") : "review";
  const issues = Array.isArray(data.critical_issues) ? data.critical_issues.slice(0, 2) : [];

  toast.custom(
    (t) => (
      <div
        className={`w-[min(92vw,460px)] rounded-2xl border bg-white p-4 shadow-2xl transition-all ${
          t.visible ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0"
        } ${ok ? "border-emerald-200" : "border-amber-200"}`}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">{provider}</p>
            <h4 className={`text-lg font-black tracking-tight ${ok ? "text-emerald-700" : "text-amber-700"}`}>{title}</h4>
          </div>
          <button
            onClick={() => toast.dismiss(t.id)}
            className="rounded-full border border-neutral-200 px-2 py-1 text-xs font-bold uppercase tracking-wide text-neutral-500 hover:border-neutral-400 hover:text-neutral-800"
          >
            Close
          </button>
        </div>

        <p className="text-sm font-medium text-neutral-700">{message}</p>

        <div className="mt-3 flex flex-wrap gap-2">
          <span className="rounded-full border border-cyan-200 bg-cyan-50 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-cyan-700">
            {bucket}
          </span>
          {typeof data.cached_reuse === "boolean" && (
            <span className="rounded-full border border-violet-200 bg-violet-50 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-violet-700">
              {data.cached_reuse ? "Reused result" : "Fresh analysis"}
            </span>
          )}
        </div>

        {issues.length > 0 && (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-xs font-medium text-rose-700">
            {issues.map((issue, idx) => (
              <li key={`${issue}-${idx}`}>{issue}</li>
            ))}
          </ul>
        )}
      </div>
    ),
    { duration: 6500, position: "top-right" },
  );
}
