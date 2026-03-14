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
  const [buying, setBuying] = useState(null);
  const [purchasedBundles, setPurchasedBundles] = useState(new Set());
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
    return () => { active = false; };
  }, [user]);

  const createBundle = async () => {
    try {
      if (!form.title.trim()) {
        toast.error("Bundle title is required");
        return;
      }
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

  const purchaseBundle = async (bundle) => {
    if (!user) {
      toast.error("Please log in to purchase");
      return;
    }
    if (purchasedBundles.has(bundle.id)) {
      toast("You already own this bundle");
      return;
    }
    const isOwner = bundle.creator_id === user?.id;
    if (isOwner) {
      toast.error("You cannot purchase your own bundle");
      return;
    }

    try {
      setBuying(bundle.id);
      const idempotencyKey = `bundle-${bundle.id}-${Date.now()}-${crypto.randomUUID()}`;

      if (bundle.price > 0) {
        // Unlock each note in the bundle using points
        let allUnlocked = true;
        for (const noteId of (bundle.note_ids || [])) {
          try {
            await api.post(
              ENDPOINTS.purchases.buy(noteId),
              { payment_method: "points" },
              { headers: { "X-Idempotency-Key": `${idempotencyKey}-${noteId}` } },
            );
          } catch (err) {
            if (!err.response?.data?.detail?.includes("Already")) {
              allUnlocked = false;
            }
          }
        }
        if (allUnlocked) {
          toast.success(`Bundle purchased! All ${bundle.note_count || "included"} notes unlocked.`);
        } else {
          toast.success("Bundle partially unlocked. Some notes may require more points.");
        }
      } else {
        // Free bundle: unlock all notes for free
        for (const noteId of (bundle.note_ids || [])) {
          try {
            await api.post(
              ENDPOINTS.purchases.buy(noteId),
              {},
              { headers: { "X-Idempotency-Key": `${idempotencyKey}-free-${noteId}` } },
            );
          } catch {
            // already purchased is fine
          }
        }
        toast.success("Free bundle unlocked!");
      }

      setPurchasedBundles((prev) => new Set([...prev, bundle.id]));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to purchase bundle");
    } finally {
      setBuying(null);
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
          <div>
            <h2 className="text-2xl font-black uppercase tracking-tight text-black">Bundles</h2>
            <p className="mt-1 text-xs font-bold uppercase tracking-wide text-zinc-500">
              Curated note collections at a bundled price
            </p>
          </div>
          {user && (
            <button onClick={() => setShowCreate((prev) => !prev)} className="btn-primary text-xs">
              {showCreate ? "Cancel" : "Create Bundle"}
            </button>
          )}
        </div>

        {showCreate && (
          <div className="border border-black bg-white p-6">
            <h3 className="mb-4 text-xl font-bold uppercase tracking-wide text-black">Create New Bundle</h3>

            <div className="space-y-4">
              <input
                className="input-surface"
                placeholder="Bundle Title *"
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
                  Select Your Approved Notes ({form.note_ids.length} selected)
                </label>
                {myNotes.length === 0 ? (
                  <p className="text-sm text-zinc-500 p-3 border border-zinc-200">
                    No approved notes available. Get some notes approved first.
                  </p>
                ) : (
                  <div className="max-h-44 space-y-2 overflow-y-auto border border-gray-200 p-3">
                    {myNotes.map((note) => (
                      <label
                        key={note.id}
                        className="flex cursor-pointer items-center border border-gray-200 p-3 hover:border-black"
                      >
                        <input
                          type="checkbox"
                          checked={form.note_ids.includes(note.id)}
                          onChange={() => toggleNote(note.id)}
                          className="mr-3"
                        />
                        <div className="flex-1">
                          <p className="font-semibold text-zinc-900">{note.title}</p>
                          <p className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                            {note.subject} · {note.dept} · Sem {note.semester}
                          </p>
                        </div>
                        <span className="text-xs font-bold text-zinc-600">
                          {note.is_paid ? `₹${note.price}` : "Free"}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="mb-1 block text-xs font-bold uppercase tracking-widest text-gray-500">
                  Bundle Price (0 = free)
                </label>
                <input
                  type="number"
                  className="input-surface"
                  placeholder="Bundle Price"
                  value={form.price}
                  onChange={(e) => setForm((prev) => ({ ...prev, price: parseInt(e.target.value, 10) || 0 }))}
                  min="0"
                  max="500"
                />
              </div>

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
            {bundles.map((bundle) => {
              const isOwner = bundle.creator_id === user?.id;
              const alreadyOwned = purchasedBundles.has(bundle.id);
              const isBuying = buying === bundle.id;

              return (
                <div key={bundle.id} className="minimal-card p-6 flex flex-col">
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <h3 className="text-lg font-bold text-zinc-900">{bundle.title}</h3>
                    {bundle.price > 0 ? (
                      <span className="border border-black bg-black px-3 py-1 text-xs font-bold text-white whitespace-nowrap">
                        ₹{bundle.price}
                      </span>
                    ) : (
                      <span className="border border-emerald-600 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700 whitespace-nowrap">
                        Free
                      </span>
                    )}
                  </div>

                  {bundle.description && (
                    <p className="mb-3 text-sm text-zinc-600 flex-1">{bundle.description}</p>
                  )}

                  <p className="text-xs font-bold uppercase tracking-wide text-zinc-500 mb-4">
                    {bundle.note_count || 0} notes included
                  </p>

                  {isOwner ? (
                    <span className="border border-zinc-200 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-zinc-500 text-center">
                      Your Bundle
                    </span>
                  ) : alreadyOwned ? (
                    <span className="border border-emerald-200 bg-emerald-50 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-emerald-700 text-center">
                      Unlocked
                    </span>
                  ) : (
                    <button
                      onClick={() => purchaseBundle(bundle)}
                      disabled={isBuying}
                      className="btn-primary text-xs w-full py-2 disabled:opacity-50"
                    >
                      {isBuying
                        ? "Unlocking..."
                        : bundle.price > 0
                        ? `Unlock with ${bundle.price} pts`
                        : "Get Free Bundle"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}
