import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import Layout from "../components/Layout";

export default function MyUploads() {
  const [notes, setNotes] = useState([]);
  const [versionDraft, setVersionDraft] = useState({});

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
    return () => {
      active = false;
    };
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

  return (
    <Layout title="My Uploads">
      <div className="mx-auto max-w-5xl space-y-8">
        {notes.length === 0 ? (
          <div className="border border-gray-200 bg-white p-16 text-center">
            <h3 className="mb-2 text-sm font-black uppercase tracking-[0.2em] text-zinc-800">No Uploads</h3>
            <p className="mx-auto mb-8 max-w-sm text-xs font-medium leading-relaxed text-zinc-500">
              Publish your first note to start building your profile.
            </p>
            <Link to="/upload-note" className="btn-primary text-xs">
              Upload Note
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {notes.map((n) => (
              <div key={n.id} className="minimal-card p-8">
                <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
                  <div>
                    <h3 className="text-2xl font-black uppercase tracking-tight text-zinc-900">{n.title}</h3>
                    <p className="mt-2 text-xs font-bold uppercase tracking-wide text-zinc-500">
                      {n.subject} • Unit {n.unit} • Semester {n.semester}
                    </p>
                  </div>

                  <div className="flex items-center gap-4">
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
                      <Link to="/viewer" state={{ note: n }} className="btn-secondary text-xs">
                        View
                      </Link>
                    )}
                  </div>
                </div>

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
                    <button onClick={() => addVersion(n.id)} className="btn-primary text-xs">Add Version</button>
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
    </Layout>
  );
}
