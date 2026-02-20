import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";

const INITIAL_FORM = {
  title: "",
  description: "",
  note_ids: [],
  price: 0,
};

export default function Bundles() {
  const [bundles, setBundles] = useState([]);
  const [myNotes, setMyNotes] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(INITIAL_FORM);
  const { user } = useAuth();

  const fetchBundles = async () => {
    try {
      const res = await api.get(ENDPOINTS.bundles.list);
      setBundles(res.data);
    } catch {
      toast.error("Failed to load bundles");
    }
  };

  useEffect(() => {
    let active = true;

    const run = async () => {
      try {
        const bundlesRes = await api.get(ENDPOINTS.bundles.list);
        if (!active) return;
        setBundles(bundlesRes.data);

        if (user) {
          const notesRes = await api.get(ENDPOINTS.notes.mine);
          if (active) setMyNotes(notesRes.data.filter((note) => note.status === "approved"));
        }
      } catch {
        toast.error("Failed to load bundle data");
      }
    };

    run();
    return () => {
      active = false;
    };
  }, [user]);

  const createBundle = async () => {
    try {
      if (form.note_ids.length < 2) {
        toast.error("Bundle needs at least 2 notes");
        return;
      }

      await api.post(ENDPOINTS.bundles.create, form);
      toast.success("Bundle created");
      setForm(INITIAL_FORM);
      setShowCreate(false);
      fetchBundles();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create bundle");
    }
  };

  const toggleNote = (noteId) => {
    setForm((prev) => ({
      ...prev,
      note_ids: prev.note_ids.includes(noteId)
        ? prev.note_ids.filter((id) => id !== noteId)
        : [...prev.note_ids, noteId],
    }));
  };

  return (
    <Layout title="Note Bundles">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-black uppercase tracking-tight text-black">Bundles</h2>
          {user && (
            <button onClick={() => setShowCreate((prev) => !prev)} className="btn-primary text-xs">
              Create Bundle
            </button>
          )}
        </div>

        {showCreate && (
          <div className="border border-black bg-white p-6">
            <h3 className="mb-4 text-xl font-bold uppercase tracking-wide text-black">Create New Bundle</h3>

            <div className="space-y-4">
              <input
                className="input-surface"
                placeholder="Bundle Title"
                value={form.title}
                onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              />

              <textarea
                className="input-surface"
                placeholder="Description (optional)"
                value={form.description}
                onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                rows={3}
              />

              <div>
                <label className="mb-2 block text-xs font-bold uppercase tracking-widest text-gray-500">
                  Select Notes ({form.note_ids.length})
                </label>
                <div className="max-h-44 space-y-2 overflow-y-auto border border-gray-200 p-3">
                  {myNotes.map((note) => (
                    <label key={note.id} className="flex cursor-pointer items-center border border-gray-200 p-3 hover:border-black">
                      <input
                        type="checkbox"
                        checked={form.note_ids.includes(note.id)}
                        onChange={() => toggleNote(note.id)}
                        className="mr-3"
                      />
                      <div className="flex-1">
                        <p className="font-semibold text-zinc-900">{note.title}</p>
                        <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                          {note.subject} • {note.dept} • Sem {note.semester}
                        </p>
                      </div>
                      <span className="text-xs font-bold text-zinc-600">{note.is_paid ? `INR ${note.price}` : "Free"}</span>
                    </label>
                  ))}
                </div>
              </div>

              <input
                type="number"
                className="input-surface"
                placeholder="Bundle Price"
                value={form.price}
                onChange={(e) => setForm((prev) => ({ ...prev, price: parseInt(e.target.value, 10) || 0 }))}
                min="0"
              />

              <div className="flex gap-3">
                <button onClick={createBundle} className="btn-primary flex-1">
                  Save Bundle
                </button>
                <button onClick={() => setShowCreate(false)} className="btn-secondary">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {bundles.length === 0 ? (
          <div className="border border-gray-200 bg-white p-12 text-center">
            <h3 className="mb-2 text-xl font-semibold text-zinc-800">No Bundles Available</h3>
            <p className="text-zinc-500">Create your first bundle to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {bundles.map((bundle) => (
              <div key={bundle.id} className="minimal-card p-6">
                <div className="mb-4 flex items-start justify-between gap-3">
                  <h3 className="text-lg font-bold text-zinc-900">{bundle.title}</h3>
                  {bundle.price > 0 && <span className="border border-black bg-black px-3 py-1 text-xs font-bold text-white">INR {bundle.price}</span>}
                </div>
                {bundle.description && <p className="mb-4 text-sm text-zinc-600">{bundle.description}</p>}
                <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">{bundle.note_count} notes</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
