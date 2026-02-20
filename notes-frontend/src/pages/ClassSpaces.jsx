import { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import toast from "react-hot-toast";

const INITIAL_SPACE = {
  name: "",
  dept: "CSE",
  semester: 3,
  section: "A",
};

export default function ClassSpaces() {
  const [spaces, setSpaces] = useState([]);
  const [createForm, setCreateForm] = useState(INITIAL_SPACE);
  const [inviteCode, setInviteCode] = useState("");
  const [selectedSpace, setSelectedSpace] = useState(null);
  const [announcements, setAnnouncements] = useState([]);
  const [newAnnouncement, setNewAnnouncement] = useState("");

  const loadSpaces = useCallback(async () => {
    try {
      const res = await api.get(ENDPOINTS.spaces.mine);
      setSpaces(res.data || []);
    } catch {
      toast.error("Failed to load spaces");
    }
  }, []);

  const loadAnnouncements = async (spaceId) => {
    try {
      const res = await api.get(ENDPOINTS.spaces.announcements(spaceId));
      setAnnouncements(res.data || []);
    } catch {
      toast.error("Failed to load announcements");
    }
  };

  useEffect(() => {
    const t = setTimeout(() => {
      loadSpaces();
    }, 0);
    return () => clearTimeout(t);
  }, [loadSpaces]);

  const createSpace = async () => {
    try {
      if (!createForm.name.trim()) {
        toast.error("Space name is required");
        return;
      }
      await api.post(ENDPOINTS.spaces.create, createForm);
      toast.success("Space created");
      setCreateForm(INITIAL_SPACE);
      loadSpaces();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create space");
    }
  };

  const joinSpace = async () => {
    try {
      if (!inviteCode.trim()) return;
      await api.post(ENDPOINTS.spaces.join(inviteCode.trim()));
      toast.success("Joined space");
      setInviteCode("");
      loadSpaces();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to join space");
    }
  };

  const postAnnouncement = async () => {
    try {
      if (!selectedSpace || !newAnnouncement.trim()) return;
      await api.post(ENDPOINTS.spaces.announcements(selectedSpace.id), { message: newAnnouncement });
      setNewAnnouncement("");
      loadAnnouncements(selectedSpace.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to post announcement");
    }
  };

  return (
    <Layout title="Class Spaces">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="border border-black bg-white p-6">
          <h3 className="mb-4 text-lg font-black uppercase tracking-wide">Create Space</h3>
          <div className="space-y-3">
            <input className="input-surface" placeholder="Space Name" value={createForm.name} onChange={(e) => setCreateForm((p) => ({ ...p, name: e.target.value }))} />
            <div className="grid grid-cols-2 gap-3">
              <input className="input-surface" placeholder="Dept" value={createForm.dept} onChange={(e) => setCreateForm((p) => ({ ...p, dept: e.target.value }))} />
              <input className="input-surface" placeholder="Section" value={createForm.section} onChange={(e) => setCreateForm((p) => ({ ...p, section: e.target.value }))} />
            </div>
            <input className="input-surface" type="number" min={1} max={8} value={createForm.semester} onChange={(e) => setCreateForm((p) => ({ ...p, semester: parseInt(e.target.value, 10) || 1 }))} />
            <button onClick={createSpace} className="btn-primary w-full">Create</button>
          </div>
          <div className="mt-8 border-t border-zinc-100 pt-4">
            <h4 className="mb-2 text-xs font-black uppercase tracking-wider text-zinc-600">Join With Invite</h4>
            <div className="flex gap-2">
              <input className="input-surface" placeholder="Invite Code" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} />
              <button onClick={joinSpace} className="btn-secondary text-xs px-4">Join</button>
            </div>
          </div>
        </div>

        <div className="border border-black bg-white p-6 lg:col-span-2">
          <h3 className="mb-4 text-lg font-black uppercase tracking-wide">My Spaces</h3>
          {spaces.length === 0 ? (
            <p className="text-sm text-zinc-500">No spaces yet.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {spaces.map((s) => (
                <button
                  key={s.id}
                  onClick={() => {
                    setSelectedSpace(s);
                    loadAnnouncements(s.id);
                  }}
                  className={`border p-4 text-left transition ${selectedSpace?.id === s.id ? "border-black bg-zinc-50" : "border-zinc-200 hover:border-black"}`}
                >
                  <p className="text-sm font-black uppercase tracking-wide text-black">{s.name}</p>
                  <p className="mt-1 text-[10px] font-bold uppercase tracking-wider text-zinc-500">{s.dept} • Sem {s.semester} • Sec {s.section || "-"}</p>
                  <p className="mt-2 text-[10px] font-bold uppercase tracking-wider text-zinc-500">Invite: {s.invite_code}</p>
                </button>
              ))}
            </div>
          )}

          {selectedSpace && (
            <div className="mt-6 border-t border-zinc-200 pt-4">
              <h4 className="mb-3 text-sm font-black uppercase tracking-wide">Announcements</h4>
              <div className="mb-3 flex gap-2">
                <input className="input-surface" placeholder="Post announcement" value={newAnnouncement} onChange={(e) => setNewAnnouncement(e.target.value)} />
                <button onClick={postAnnouncement} className="btn-primary text-xs px-4">Post</button>
              </div>
              <div className="max-h-64 space-y-2 overflow-y-auto">
                {announcements.map((a) => (
                  <div key={a.id} className="border border-zinc-200 p-3">
                    <p className="text-sm text-zinc-800">{a.message}</p>
                    <p className="mt-1 text-[10px] font-bold uppercase tracking-wider text-zinc-500">{new Date(a.created_at * 1000).toLocaleString()}</p>
                  </div>
                ))}
                {announcements.length === 0 && (
                  <p className="text-xs text-zinc-500">No announcements yet.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
