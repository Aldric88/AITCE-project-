import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import Layout from "../components/Layout";

const STATUS_FILTERS = ["all", "pending", "approved", "rejected"];

export default function MyUploads() {
  const [notes, setNotes] = useState([]);
  const [filter, setFilter] = useState("all");
  const [versionDraft, setVersionDraft] = useState({});
  const [deletingId, setDeletingId] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const fetchNotes = async () => {
    try {
      const res = await api.get(ENDPOINTS.notes.mine);
      setNotes(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load uploads");
    }
  };

  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const res = await api.get(ENDPOINTS.notes.mine);
        if (active) setNotes(res.data);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to load uploads");
      }
    };
    run();
    return () => { active = false; };
  }, []);

  const addVersion = async (noteId) => {
    const draft = versionDraft[noteId] || {};
    try {
      if (!draft.file_url?.trim()) {
        toast.error("File URL is required for new version");
        return;
      }
      await api.post(ENDPOINTS.notes.versions(noteId), {
        file_url: draft.file_url.trim(),
        changelog: draft.changelog || "",
      });
      toast.success("Version added");
      setVersionDraft((prev) => ({ ...prev, [noteId]: { file_url: "", changelog: "" } }));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add version");
    }
  };

  const deleteNote = async (noteId) => {
    try {
      setDeletingId(noteId);
      await api.delete(`/notes/${noteId}`);
      toast.success("Note deleted");
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
      setConfirmDelete(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete note");
    } finally {
      setDeletingId(null);
    }
  };

  const filteredNotes = filter === "all" ? notes : notes.filter((n) => n.status === filter);

  const statusCounts = notes.reduce((acc, n) => {
    acc[n.status] = (acc[n.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <Layout title="My Uploads">
      <div className="mx-auto max-w-5xl space-y-6">
        {/* Header + Stats */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-black uppercase tracking-tight text-black">My Uploads</h2>
            <p className="mt-1 text-xs font-bold uppercase tracking-wide text-zinc-500">
              {notes.length} notes total
            </p>
          </div>
          <Link to="/upload-note" className="btn-primary text-xs px-4 py-2">
            Upload New
          </Link>
        </div>

        {/* Status summary */}
        {notes.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            {[
              { key: "approved", label: "Approved", color: "emerald" },
              { key: "pending", label: "Pending", color: "amber" },
              { key: "rejected", label: "Rejected", color: "red" },
            ].map(({ key, label, color }) => (
              <div key={key} className={`border p-3 text-center border-${color}-200 bg-${color}-50`}>
                <p className={`text-2xl font-black text-${color}-700`}>{statusCounts[key] || 0}</p>
                <p className={`text-[10px] font-black uppercase tracking-widest text-${color}-600`}>{label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filter tabs */}
        {notes.length > 0 && (
          <div className="flex gap-2 flex-wrap">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`px-4 py-1.5 text-[10px] font-black uppercase tracking-widest border transition ${
                  filter === s
                    ? "border-black bg-black text-white"
                    : "border-zinc-300 bg-white text-zinc-600 hover:border-black"
                }`}
              >
                {s === "all" ? `All (${notes.length})` : `${s} (${statusCounts[s] || 0})`}
              </button>
            ))}
          </div>
        )}

        {filteredNotes.length === 0 ? (
          <div className="border border-gray-200 bg-white p-16 text-center">
            <h3 className="mb-2 text-sm font-black uppercase tracking-[0.2em] text-zinc-800">
              {notes.length === 0 ? "No Uploads" : `No ${filter} notes`}
            </h3>
            <p className="mx-auto mb-8 max-w-sm text-xs font-medium leading-relaxed text-zinc-500">
              {notes.length === 0
                ? "Publish your first note to start building your profile."
                : `You have no ${filter} notes right now.`}
            </p>
            {notes.length === 0 && (
              <Link to="/upload-note" className="btn-primary text-xs">
                Upload Note
              </Link>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {filteredNotes.map((n) => (
              <div key={n.id} className="minimal-card p-8">
                <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-start">
                  <div className="flex-1">
                    <h3 className="text-2xl font-black uppercase tracking-tight text-zinc-900">{n.title}</h3>
                    <p className="mt-2 text-xs font-bold uppercase tracking-wide text-zinc-500">
                      {n.subject} · Unit {n.unit} · Semester {n.semester}
                    </p>
                    {n.is_paid && (
                      <p className="mt-1 text-xs font-bold uppercase tracking-wide text-zinc-600">
                        ₹{n.price} · Paid Note
                      </p>
                    )}
                    {n.status === "rejected" && n.rejected_reason && (
                      <p className="mt-2 text-xs font-bold text-red-600">
                        Reason: {n.rejected_reason}
                      </p>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 shrink-0">
                    <span
                      className={`inline-block border px-4 py-2 text-[10px] font-black uppercase tracking-widest ${
                        n.status === "approved"
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                          : n.status === "rejected"
                          ? "border-red-200 bg-red-50 text-red-700"
                          : "border-amber-200 bg-amber-50 text-amber-700"
                      }`}
                    >
                      {n.status}
                    </span>

                    {n.file_url && (
                      <Link to="/viewer" state={{ note: n }} className="btn-secondary text-xs px-3 py-2">
                        View
                      </Link>
                    )}

                    {n.status === "rejected" && (
                      <Link to="/rejected-notes" className="btn-secondary text-xs px-3 py-2 border-red-300 text-red-700 hover:bg-red-50">
                        Appeal
                      </Link>
                    )}

                    <button
                      onClick={() => setConfirmDelete(n)}
                      className="btn-secondary text-xs px-3 py-2 border-red-200 text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {/* Stats row for approved notes */}
                {n.status === "approved" && (
                  <div className="mt-4 flex gap-6 text-xs font-bold uppercase tracking-wider text-zinc-500">
                    <span>Views: <b className="text-zinc-800">{n.views || 0}</b></span>
                    <span>Downloads: <b className="text-zinc-800">{n.downloads || 0}</b></span>
                    {n.avg_rating > 0 && (
                      <span>Rating: <b className="text-zinc-800">{n.avg_rating}/5</b></span>
                    )}
                  </div>
                )}

                <div className="mt-5 border-t border-zinc-100 pt-4">
                  <p className="mb-2 text-[10px] font-black uppercase tracking-wider text-zinc-500">Publish New Version</p>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
                    <input
                      className="input-surface md:col-span-2"
                      placeholder="New file_url from upload step"
                      value={versionDraft[n.id]?.file_url || ""}
                      onChange={(e) =>
                        setVersionDraft((prev) => ({
                          ...prev,
                          [n.id]: { ...(prev[n.id] || {}), file_url: e.target.value },
                        }))
                      }
                    />
                    <button onClick={() => addVersion(n.id)} className="btn-primary text-xs">
                      Add Version
                    </button>
                    <input
                      className="input-surface md:col-span-3"
                      placeholder="Changelog (optional)"
                      value={versionDraft[n.id]?.changelog || ""}
                      onChange={(e) =>
                        setVersionDraft((prev) => ({
                          ...prev,
                          [n.id]: { ...(prev[n.id] || {}), changelog: e.target.value },
                        }))
                      }
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm border border-black bg-white">
            <div className="border-b border-black p-4">
              <h3 className="text-sm font-black uppercase tracking-wider text-black">Confirm Delete</h3>
            </div>
            <div className="p-6 space-y-4">
              <p className="text-sm text-zinc-700">
                Are you sure you want to delete{" "}
                <span className="font-bold">"{confirmDelete.title}"</span>?
                This action cannot be undone.
              </p>
              {confirmDelete.status === "approved" && (
                <div className="bg-amber-50 border border-amber-200 p-3">
                  <p className="text-xs font-bold text-amber-700">
                    Warning: This is an approved note. Deleting it will remove it from the public feed and any buyer access.
                  </p>
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => deleteNote(confirmDelete.id)}
                  disabled={deletingId === confirmDelete.id}
                  className="flex-1 border border-red-600 bg-red-600 px-4 py-2 text-xs font-black uppercase tracking-widest text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {deletingId === confirmDelete.id ? "Deleting..." : "Delete"}
                </button>
                <button
                  onClick={() => setConfirmDelete(null)}
                  className="btn-secondary text-xs px-4"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
