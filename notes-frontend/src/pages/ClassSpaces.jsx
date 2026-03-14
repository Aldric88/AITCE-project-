import { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import toast from "react-hot-toast";

const INITIAL_SPACE = { name: "", dept: "CSE", semester: 3, section: "" };

const ROLE_BADGE = {
  owner: "border-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400",
  moderator: "border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400",
  member: "border-zinc-300 dark:border-zinc-600 bg-zinc-50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400",
};

// ── Small sub-components ──────────────────────────────────────────────────────

function RoleBadge({ role }) {
  return (
    <span className={`inline-flex items-center border px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${ROLE_BADGE[role] || ROLE_BADGE.member}`}>
      {role}
    </span>
  );
}

function SectionHeader({ children }) {
  return (
    <h3 className="mb-4 text-xs font-black uppercase tracking-widest text-zinc-500 dark:text-zinc-400 border-b border-zinc-100 dark:border-zinc-800 pb-2">
      {children}
    </h3>
  );
}

function EmptyState({ text }) {
  return <p className="text-xs text-zinc-400 dark:text-zinc-600 uppercase tracking-wide">{text}</p>;
}

/** Inline confirmation dialog — replaces all window.confirm() calls */
function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-80 border border-black dark:border-zinc-600 bg-white dark:bg-zinc-900 p-6 shadow-[8px_8px_0px_0px_rgba(0,0,0,0.15)]">
        <p className="mb-5 text-sm font-bold text-black dark:text-white leading-relaxed">{message}</p>
        <div className="flex gap-2">
          <button
            onClick={onConfirm}
            className="flex-1 bg-black dark:bg-white py-2 text-xs font-black uppercase tracking-wide text-white dark:text-black hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-colors"
          >
            Confirm
          </button>
          <button
            onClick={onCancel}
            className="flex-1 border border-zinc-300 dark:border-zinc-600 py-2 text-xs font-black uppercase tracking-wide text-zinc-600 dark:text-zinc-400 hover:border-black dark:hover:border-white hover:text-black dark:hover:text-white transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ClassSpaces() {
  const [spaces, setSpaces] = useState([]);
  const [loadingSpaces, setLoadingSpaces] = useState(true);

  // Create / join
  const [createForm, setCreateForm] = useState(INITIAL_SPACE);
  const [inviteCode, setInviteCode] = useState("");
  const [creating, setCreating] = useState(false);
  const [joining, setJoining] = useState(false);

  // Active space panel
  const [selected, setSelected] = useState(null);

  // Tabs inside a space
  const [tab, setTab] = useState("announcements");

  // Announcements
  const [announcements, setAnnouncements] = useState([]);
  const [loadingAnn, setLoadingAnn] = useState(false);
  const [newAnnouncement, setNewAnnouncement] = useState("");
  const [postingAnn, setPostingAnn] = useState(false);

  // Members
  const [members, setMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(false);

  // Shared notes
  const [spaceNotes, setSpaceNotes] = useState([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [myNotes, setMyNotes] = useState([]); // user's own uploads for the picker
  const [loadingMyNotes, setLoadingMyNotes] = useState(false);
  const [shareNoteId, setShareNoteId] = useState("");
  const [sharing, setSharing] = useState(false);

  // Edit space
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState({});

  // Inline confirmation dialog
  const [confirm, setConfirm] = useState(null); // { message, onConfirm }

  const askConfirm = (message, onConfirm) => setConfirm({ message, onConfirm });

  // ── Data loaders ──────────────────────────────────────────────────────────

  const loadSpaces = useCallback(async () => {
    setLoadingSpaces(true);
    try {
      const res = await api.get(ENDPOINTS.spaces.mine);
      setSpaces(res.data || []);
    } catch {
      toast.error("Failed to load spaces", { id: "spaces-load-error" });
    } finally {
      setLoadingSpaces(false);
    }
  }, []);

  useEffect(() => { loadSpaces(); }, [loadSpaces]);

  const loadAnnouncements = useCallback(async (spaceId) => {
    setLoadingAnn(true);
    try {
      const res = await api.get(ENDPOINTS.spaces.announcements(spaceId));
      setAnnouncements(res.data || []);
    } catch {
      toast.error("Failed to load announcements", { id: "ann-load-error" });
    } finally {
      setLoadingAnn(false);
    }
  }, []);

  const loadMembers = useCallback(async (spaceId) => {
    setLoadingMembers(true);
    try {
      const res = await api.get(ENDPOINTS.spaces.members(spaceId));
      setMembers(res.data || []);
    } catch {
      toast.error("Failed to load members", { id: "members-load-error" });
    } finally {
      setLoadingMembers(false);
    }
  }, []);

  const loadSpaceNotes = useCallback(async (spaceId) => {
    setLoadingNotes(true);
    try {
      const res = await api.get(ENDPOINTS.spaces.notes(spaceId));
      setSpaceNotes(res.data || []);
    } catch {
      toast.error("Failed to load shared notes", { id: "space-notes-load-error" });
    } finally {
      setLoadingNotes(false);
    }
  }, []);

  const loadMyNotes = useCallback(async () => {
    if (myNotes.length > 0) return; // already loaded
    setLoadingMyNotes(true);
    try {
      const res = await api.get(ENDPOINTS.notes.mine);
      setMyNotes((res.data || []).filter((n) => n.status === "approved"));
    } catch {
      // non-critical
    } finally {
      setLoadingMyNotes(false);
    }
  }, [myNotes.length]);

  // When a space is selected, reset and load announcements
  const selectSpace = (space) => {
    setSelected(space);
    setTab("announcements");
    setEditMode(false);
    setAnnouncements([]);
    setMembers([]);
    setSpaceNotes([]);
    loadAnnouncements(space.id);
  };

  // When tab changes inside a selected space, load tab data
  useEffect(() => {
    if (!selected) return;
    if (tab === "announcements") loadAnnouncements(selected.id);
    else if (tab === "members") loadMembers(selected.id);
    else if (tab === "notes") {
      loadSpaceNotes(selected.id);
      loadMyNotes();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, selected?.id]);

  // ── Actions ───────────────────────────────────────────────────────────────

  const createSpace = async () => {
    if (!createForm.name.trim()) { toast.error("Space name is required"); return; }
    setCreating(true);
    try {
      await api.post(ENDPOINTS.spaces.create, createForm);
      toast.success("Space created");
      setCreateForm(INITIAL_SPACE);
      loadSpaces();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create space");
    } finally {
      setCreating(false);
    }
  };

  const joinSpace = async () => {
    if (!inviteCode.trim()) return;
    setJoining(true);
    try {
      await api.post(ENDPOINTS.spaces.join(inviteCode.trim()));
      toast.success("Joined space");
      setInviteCode("");
      loadSpaces();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to join space");
    } finally {
      setJoining(false);
    }
  };

  const leaveSpace = () => {
    if (!selected) return;
    askConfirm(`Leave "${selected.name}"?`, async () => {
      setConfirm(null);
      try {
        await api.post(ENDPOINTS.spaces.leave(selected.id));
        toast.success("Left space");
        setSelected(null);
        loadSpaces();
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to leave space");
      }
    });
  };

  const deleteSpace = () => {
    if (!selected) return;
    askConfirm(`Permanently delete "${selected.name}"? This cannot be undone.`, async () => {
      setConfirm(null);
      try {
        await api.delete(ENDPOINTS.spaces.delete(selected.id));
        toast.success("Space deleted");
        setSelected(null);
        loadSpaces();
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to delete space");
      }
    });
  };

  const saveEdit = async () => {
    if (!selected) return;
    try {
      await api.patch(ENDPOINTS.spaces.update(selected.id), editForm);
      toast.success("Space updated");
      setEditMode(false);
      const updated = { ...selected, ...editForm };
      setSelected(updated);
      setSpaces((prev) => prev.map((s) => s.id === updated.id ? updated : s));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update space");
    }
  };

  const regenerateInvite = () => {
    if (!selected) return;
    askConfirm("Regenerate invite code? The old code will stop working immediately.", async () => {
      setConfirm(null);
      try {
        const res = await api.post(ENDPOINTS.spaces.regenerateInvite(selected.id));
        const newCode = res.data.invite_code;
        toast.success("Invite code regenerated");
        const updated = { ...selected, invite_code: newCode };
        setSelected(updated);
        setSpaces((prev) => prev.map((s) => s.id === updated.id ? updated : s));
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to regenerate invite");
      }
    });
  };

  const postAnnouncement = async () => {
    if (!selected || !newAnnouncement.trim()) return;
    setPostingAnn(true);
    try {
      await api.post(ENDPOINTS.spaces.announcements(selected.id), { message: newAnnouncement });
      setNewAnnouncement("");
      loadAnnouncements(selected.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to post announcement");
    } finally {
      setPostingAnn(false);
    }
  };

  const deleteAnnouncement = async (annId) => {
    if (!selected) return;
    try {
      await api.delete(ENDPOINTS.spaces.deleteAnnouncement(selected.id, annId));
      setAnnouncements((prev) => prev.filter((a) => a.id !== annId));
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to delete announcement");
    }
  };

  const kickMember = (userId, name) => {
    if (!selected) return;
    askConfirm(`Remove ${name} from this space?`, async () => {
      setConfirm(null);
      try {
        await api.delete(ENDPOINTS.spaces.kickMember(selected.id, userId));
        toast.success(`${name} removed`);
        loadMembers(selected.id);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to remove member");
      }
    });
  };

  const promoteMember = async (userId, currentRole) => {
    if (!selected) return;
    const newRole = currentRole === "member" ? "moderator" : "member";
    try {
      await api.patch(`${ENDPOINTS.spaces.updateMemberRole(selected.id, userId)}?role=${newRole}`);
      toast.success(`Role updated to ${newRole}`);
      loadMembers(selected.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update role");
    }
  };

  const transferOwnership = (userId, name) => {
    if (!selected) return;
    askConfirm(`Transfer ownership to ${name}? You will become a regular member.`, async () => {
      setConfirm(null);
      try {
        await api.post(ENDPOINTS.spaces.transferOwnership(selected.id, userId));
        toast.success(`Ownership transferred to ${name}`);
        // Refresh both spaces list and members
        const updatedSpace = { ...selected, role: "member" };
        setSelected(updatedSpace);
        setSpaces((prev) => prev.map((s) => s.id === updatedSpace.id ? updatedSpace : s));
        loadMembers(selected.id);
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to transfer ownership");
      }
    });
  };

  const shareNote = async () => {
    if (!selected || !shareNoteId.trim()) return;
    setSharing(true);
    try {
      await api.post(ENDPOINTS.spaces.notes(selected.id), { note_id: shareNoteId.trim() });
      toast.success("Note shared");
      setShareNoteId("");
      loadSpaceNotes(selected.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to share note");
    } finally {
      setSharing(false);
    }
  };

  const removeSharedNote = (shareId, title) => {
    if (!selected) return;
    askConfirm(`Remove "${title}" from this space?`, async () => {
      setConfirm(null);
      try {
        await api.delete(ENDPOINTS.spaces.removeSharedNote(selected.id, shareId));
        setSpaceNotes((prev) => prev.filter((n) => n.id !== shareId));
      } catch (err) {
        toast.error(err.response?.data?.detail || "Failed to remove note");
      }
    });
  };

  const copyInvite = () => {
    if (!selected) return;
    navigator.clipboard.writeText(selected.invite_code);
    toast.success("Invite code copied");
  };

  // ── Render helpers ────────────────────────────────────────────────────────

  const isPrivileged = selected && ["owner", "moderator"].includes(selected.role);
  const isOwner = selected?.role === "owner";

  const TABS = ["announcements", "members", "notes"];

  return (
    <Layout title="Class Spaces">
      {/* Inline confirmation dialog */}
      {confirm && (
        <ConfirmDialog
          message={confirm.message}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
        />
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        {/* ── Left panel: Create + Join + Space List ── */}
        <div className="space-y-4">

          {/* Create */}
          <div className="border border-black dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5">
            <SectionHeader>Create Space</SectionHeader>
            <div className="space-y-3">
              <input
                className="input-field w-full rounded-none border-black dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                placeholder="Space Name (e.g. CSE Sem 5 - G1)"
                value={createForm.name}
                onChange={(e) => setCreateForm((p) => ({ ...p, name: e.target.value }))}
                onKeyDown={(e) => e.key === "Enter" && createSpace()}
              />
              <div className="grid grid-cols-3 gap-2">
                <input
                  className="input-field rounded-none border-black dark:border-zinc-600 dark:bg-zinc-800 dark:text-white col-span-1"
                  placeholder="Dept"
                  value={createForm.dept}
                  onChange={(e) => setCreateForm((p) => ({ ...p, dept: e.target.value }))}
                />
                <select
                  className="input-field rounded-none border-black dark:border-zinc-600 dark:bg-zinc-800 dark:text-white col-span-1"
                  value={createForm.semester}
                  onChange={(e) => setCreateForm((p) => ({ ...p, semester: parseInt(e.target.value, 10) }))}
                >
                  {[1,2,3,4,5,6,7,8].map((s) => <option key={s} value={s}>Sem {s}</option>)}
                </select>
                <input
                  className="input-field rounded-none border-black dark:border-zinc-600 dark:bg-zinc-800 dark:text-white col-span-1"
                  placeholder="Section"
                  value={createForm.section}
                  onChange={(e) => setCreateForm((p) => ({ ...p, section: e.target.value }))}
                />
              </div>
              <button
                onClick={createSpace}
                disabled={creating}
                className="btn-primary w-full rounded-none text-xs tracking-widest disabled:opacity-50"
              >
                {creating ? "Creating..." : "Create Space"}
              </button>
            </div>

            <div className="mt-5 border-t border-zinc-100 dark:border-zinc-800 pt-4">
              <p className="mb-2 text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">Join with Invite Code</p>
              <div className="flex gap-2">
                <input
                  className="input-field flex-1 rounded-none border-black dark:border-zinc-600 dark:bg-zinc-800 dark:text-white font-mono uppercase"
                  placeholder="e.g. a3f2b1c8"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && joinSpace()}
                />
                <button
                  onClick={joinSpace}
                  disabled={joining}
                  className="border border-black dark:border-zinc-600 px-4 text-xs font-black uppercase tracking-wide text-black dark:text-white hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors disabled:opacity-40"
                >
                  {joining ? "..." : "Join"}
                </button>
              </div>
            </div>
          </div>

          {/* Space list */}
          <div className="border border-black dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5">
            <SectionHeader>My Spaces</SectionHeader>
            {loadingSpaces ? (
              <div className="space-y-2">
                {[1,2,3].map((i) => (
                  <div key={i} className="h-16 bg-zinc-100 dark:bg-zinc-800 animate-pulse" />
                ))}
              </div>
            ) : spaces.length === 0 ? (
              <EmptyState text="No spaces yet. Create or join one." />
            ) : (
              <div className="space-y-2">
                {spaces.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => selectSpace(s)}
                    className={`w-full border p-3 text-left transition-all ${
                      selected?.id === s.id
                        ? "border-black dark:border-white bg-black dark:bg-white"
                        : "border-zinc-200 dark:border-zinc-700 hover:border-black dark:hover:border-zinc-400"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className={`text-sm font-black uppercase tracking-wide truncate ${selected?.id === s.id ? "text-white dark:text-black" : "text-black dark:text-white"}`}>
                        {s.name}
                      </p>
                      <RoleBadge role={s.role} />
                    </div>
                    <p className={`mt-1 text-[10px] font-bold uppercase tracking-wider ${selected?.id === s.id ? "text-zinc-300 dark:text-zinc-600" : "text-zinc-500 dark:text-zinc-400"}`}>
                      {s.dept} · Sem {s.semester}{s.section ? ` · ${s.section}` : ""} · {s.member_count} member{s.member_count !== 1 ? "s" : ""}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Right panel: Space detail ── */}
        <div className="lg:col-span-2">
          {!selected ? (
            <div className="border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 p-12 text-center">
              <p className="text-xs font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-600">
                Select a space to view its content
              </p>
            </div>
          ) : (
            <div className="border border-black dark:border-zinc-700 bg-white dark:bg-zinc-900">

              {/* Space header */}
              <div className="border-b border-black dark:border-zinc-700 bg-black dark:bg-white p-5">
                {editMode ? (
                  <div className="space-y-3">
                    <input
                      className="w-full border border-zinc-600 bg-zinc-900 px-3 py-2 text-sm font-bold text-white focus:outline-none focus:border-white"
                      value={editForm.name ?? selected.name}
                      onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))}
                    />
                    <div className="grid grid-cols-3 gap-2">
                      <input
                        className="border border-zinc-600 bg-zinc-900 px-3 py-2 text-xs font-bold text-white focus:outline-none"
                        value={editForm.dept ?? selected.dept}
                        onChange={(e) => setEditForm((p) => ({ ...p, dept: e.target.value }))}
                        placeholder="Dept"
                      />
                      <select
                        className="border border-zinc-600 bg-zinc-900 px-3 py-2 text-xs font-bold text-white focus:outline-none"
                        value={editForm.semester ?? selected.semester}
                        onChange={(e) => setEditForm((p) => ({ ...p, semester: parseInt(e.target.value, 10) }))}
                      >
                        {[1,2,3,4,5,6,7,8].map((s) => <option key={s} value={s}>Sem {s}</option>)}
                      </select>
                      <input
                        className="border border-zinc-600 bg-zinc-900 px-3 py-2 text-xs font-bold text-white focus:outline-none"
                        value={editForm.section ?? selected.section ?? ""}
                        onChange={(e) => setEditForm((p) => ({ ...p, section: e.target.value }))}
                        placeholder="Section"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button onClick={saveEdit} className="border border-white px-4 py-1.5 text-xs font-black uppercase text-white hover:bg-white hover:text-black transition-colors">Save</button>
                      <button onClick={() => setEditMode(false)} className="border border-zinc-600 px-4 py-1.5 text-xs font-black uppercase text-zinc-400 hover:border-zinc-400 hover:text-white transition-colors">Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h2 className="text-2xl font-black uppercase tracking-tight text-white dark:text-black">{selected.name}</h2>
                      <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-600">
                        {selected.dept} · Sem {selected.semester}{selected.section ? ` · ${selected.section}` : ""} · {selected.member_count} member{selected.member_count !== 1 ? "s" : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <RoleBadge role={selected.role} />
                      {isOwner && (
                        <button
                          onClick={() => { setEditMode(true); setEditForm({}); }}
                          className="border border-zinc-600 dark:border-zinc-400 px-2 py-1 text-[10px] font-black uppercase tracking-wide text-zinc-400 dark:text-zinc-600 hover:border-white hover:text-white dark:hover:border-black dark:hover:text-black transition-colors"
                        >
                          Edit
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Invite code row */}
                <div className="mt-4 flex items-center gap-3 border-t border-zinc-800 dark:border-zinc-200 pt-3">
                  <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500 dark:text-zinc-400">Invite:</span>
                  <code className="font-mono text-sm font-bold text-white dark:text-black tracking-widest">{selected.invite_code}</code>
                  <button
                    onClick={copyInvite}
                    className="text-[10px] font-black uppercase tracking-wide text-zinc-400 dark:text-zinc-600 hover:text-white dark:hover:text-black transition-colors border border-zinc-700 dark:border-zinc-300 px-2 py-0.5"
                  >
                    Copy
                  </button>
                  {isOwner && (
                    <button
                      onClick={regenerateInvite}
                      className="text-[10px] font-black uppercase tracking-wide text-zinc-400 dark:text-zinc-600 hover:text-white dark:hover:text-black transition-colors border border-zinc-700 dark:border-zinc-300 px-2 py-0.5"
                    >
                      Regenerate
                    </button>
                  )}
                  <div className="ml-auto flex gap-2">
                    {!isOwner && (
                      <button
                        onClick={leaveSpace}
                        className="text-[10px] font-black uppercase tracking-wide text-red-400 hover:text-white dark:hover:text-black border border-red-800 dark:border-red-400 hover:border-red-400 px-2 py-0.5 transition-colors"
                      >
                        Leave
                      </button>
                    )}
                    {isOwner && (
                      <button
                        onClick={deleteSpace}
                        className="text-[10px] font-black uppercase tracking-wide text-red-400 hover:text-white dark:hover:text-black border border-red-800 dark:border-red-400 hover:border-red-400 px-2 py-0.5 transition-colors"
                      >
                        Delete Space
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-zinc-100 dark:border-zinc-800">
                {TABS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`flex-1 py-3 text-[10px] font-black uppercase tracking-widest transition-colors ${
                      tab === t
                        ? "border-b-2 border-black dark:border-white text-black dark:text-white"
                        : "text-zinc-400 dark:text-zinc-600 hover:text-black dark:hover:text-white"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="p-5">

                {/* ── ANNOUNCEMENTS ── */}
                {tab === "announcements" && (
                  <div className="space-y-4">
                    {isPrivileged && (
                      <div className="flex gap-2">
                        <input
                          className="input-field flex-1 rounded-none border-black dark:border-zinc-600 dark:bg-zinc-800 dark:text-white"
                          placeholder="Post an announcement..."
                          value={newAnnouncement}
                          onChange={(e) => setNewAnnouncement(e.target.value)}
                          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && postAnnouncement()}
                        />
                        <button
                          onClick={postAnnouncement}
                          disabled={postingAnn || !newAnnouncement.trim()}
                          className="btn-primary rounded-none px-5 text-xs tracking-widest disabled:opacity-40"
                        >
                          {postingAnn ? "..." : "Post"}
                        </button>
                      </div>
                    )}

                    {loadingAnn ? (
                      <div className="space-y-2">
                        {[1,2,3].map((i) => <div key={i} className="h-14 bg-zinc-100 dark:bg-zinc-800 animate-pulse" />)}
                      </div>
                    ) : announcements.length === 0 ? (
                      <EmptyState text="No announcements yet." />
                    ) : (
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {announcements.map((a) => (
                          <div key={a.id} className="border border-zinc-100 dark:border-zinc-800 p-3 group">
                            <div className="flex items-start justify-between gap-2">
                              <p className="text-sm text-black dark:text-white leading-relaxed">{a.message}</p>
                              {isPrivileged && (
                                <button
                                  onClick={() => deleteAnnouncement(a.id)}
                                  className="hidden group-hover:block text-[10px] font-black uppercase text-red-400 hover:text-red-600 flex-shrink-0"
                                >
                                  ✕
                                </button>
                              )}
                            </div>
                            <p className="mt-1.5 text-[10px] font-bold uppercase tracking-wide text-zinc-400 dark:text-zinc-600">
                              {a.created_by_name} · {new Date(a.created_at * 1000).toLocaleString()}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* ── MEMBERS ── */}
                {tab === "members" && (
                  <div className="space-y-3">
                    {loadingMembers ? (
                      <div className="space-y-2">
                        {[1,2,3].map((i) => <div key={i} className="h-12 bg-zinc-100 dark:bg-zinc-800 animate-pulse" />)}
                      </div>
                    ) : members.length === 0 ? (
                      <EmptyState text="No members found." />
                    ) : (
                      members.map((m) => (
                        <div key={m.user_id} className="flex items-center justify-between gap-2 border border-zinc-100 dark:border-zinc-800 px-3 py-2.5">
                          <div className="min-w-0">
                            <p className="text-sm font-bold text-black dark:text-white truncate">{m.name}</p>
                            <p className="text-[10px] font-medium text-zinc-400 dark:text-zinc-600 uppercase tracking-wide truncate">{m.email}</p>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <RoleBadge role={m.role} />
                            {isOwner && m.role !== "owner" && (
                              <>
                                <button
                                  onClick={() => promoteMember(m.user_id, m.role)}
                                  className="text-[10px] font-black uppercase tracking-wide text-blue-500 hover:text-blue-700 border border-blue-200 dark:border-blue-800 px-2 py-0.5 transition-colors"
                                >
                                  {m.role === "member" ? "Promote" : "Demote"}
                                </button>
                                <button
                                  onClick={() => transferOwnership(m.user_id, m.name)}
                                  className="text-[10px] font-black uppercase tracking-wide text-yellow-600 hover:text-yellow-800 dark:text-yellow-400 dark:hover:text-yellow-300 border border-yellow-300 dark:border-yellow-700 px-2 py-0.5 transition-colors"
                                >
                                  Make Owner
                                </button>
                                <button
                                  onClick={() => kickMember(m.user_id, m.name)}
                                  className="text-[10px] font-black uppercase tracking-wide text-red-400 hover:text-red-600 border border-red-200 dark:border-red-800 px-2 py-0.5 transition-colors"
                                >
                                  Kick
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* ── SHARED NOTES ── */}
                {tab === "notes" && (
                  <div className="space-y-4">
                    {/* Note picker */}
                    <div>
                      <p className="mb-1 text-[10px] font-black uppercase tracking-widest text-zinc-400 dark:text-zinc-500">
                        Share one of your notes with this space
                      </p>
                      <div className="flex gap-2">
                        {loadingMyNotes ? (
                          <div className="flex-1 h-10 bg-zinc-100 dark:bg-zinc-800 animate-pulse" />
                        ) : myNotes.length === 0 ? (
                          <p className="flex-1 text-xs text-zinc-400 dark:text-zinc-600 py-2">
                            You have no approved notes to share yet.
                          </p>
                        ) : (
                          <select
                            className="flex-1 border border-black dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-xs font-bold text-black dark:text-white focus:outline-none focus:border-black dark:focus:border-white"
                            value={shareNoteId}
                            onChange={(e) => setShareNoteId(e.target.value)}
                          >
                            <option value="">Select a note to share...</option>
                            {myNotes.map((n) => (
                              <option key={n.id} value={n.id}>
                                {n.title}{n.subject ? ` — ${n.subject}` : ""}{n.semester ? ` (Sem ${n.semester})` : ""}
                              </option>
                            ))}
                          </select>
                        )}
                        <button
                          onClick={shareNote}
                          disabled={sharing || !shareNoteId.trim()}
                          className="btn-primary rounded-none px-5 text-xs tracking-widest disabled:opacity-40"
                        >
                          {sharing ? "..." : "Share"}
                        </button>
                      </div>
                      <p className="mt-1 text-[10px] text-zinc-400 dark:text-zinc-600">
                        Only your approved notes are listed. Other members can view and access them from here.
                      </p>
                    </div>

                    {loadingNotes ? (
                      <div className="space-y-2">
                        {[1,2,3].map((i) => <div key={i} className="h-16 bg-zinc-100 dark:bg-zinc-800 animate-pulse" />)}
                      </div>
                    ) : spaceNotes.length === 0 ? (
                      <EmptyState text="No notes shared yet." />
                    ) : (
                      <div className="space-y-2 max-h-96 overflow-y-auto">
                        {spaceNotes.map((n) => (
                          <div key={n.id} className="border border-zinc-100 dark:border-zinc-800 p-3 flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-bold text-black dark:text-white truncate">{n.title}</p>
                              <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wide text-zinc-400 dark:text-zinc-600">
                                {n.subject} · Sem {n.semester} · {n.is_paid ? `INR ${n.price}` : "Free"}
                              </p>
                              <p className="mt-0.5 text-[10px] text-zinc-400 dark:text-zinc-600">
                                Shared by {n.shared_by_name} · {new Date(n.shared_at * 1000).toLocaleDateString()}
                              </p>
                            </div>
                            <div className="flex gap-2 flex-shrink-0">
                              <a
                                href={`/notes/${n.note_id}`}
                                className="text-[10px] font-black uppercase tracking-wide border border-zinc-300 dark:border-zinc-600 px-2 py-0.5 text-black dark:text-white hover:bg-black hover:text-white dark:hover:bg-white dark:hover:text-black transition-colors"
                              >
                                View
                              </a>
                              {isPrivileged && (
                                <button
                                  onClick={() => removeSharedNote(n.id, n.title)}
                                  className="text-[10px] font-black uppercase tracking-wide text-red-400 hover:text-red-600 border border-red-200 dark:border-red-800 px-2 py-0.5 transition-colors"
                                >
                                  Remove
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

              </div>
            </div>
          )}
        </div>

      </div>
    </Layout>
  );
}
