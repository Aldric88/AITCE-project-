import { useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { API_BASE_URL } from "../api/baseUrl";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";
import PeopleModal from "../components/PeopleModal";

const DEPT_OPTIONS = ["CSE", "ECE", "EEE", "MECH", "CIVIL", "IT", "AIML", "DS", "OTHER"];

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [peopleOpen, setPeopleOpen] = useState(false);
  const [peopleTitle, setPeopleTitle] = useState("");
  const [people, setPeople] = useState([]);
  const [peopleLoading, setPeopleLoading] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "",
    dept: "",
    year: "",
    section: "",
  });

  const openEdit = () => {
    setEditForm({
      name: user?.name || "",
      dept: user?.dept || "",
      year: user?.year ? String(user.year) : "",
      section: user?.section || "",
    });
    setEditOpen(true);
  };

  const saveProfile = async () => {
    const payload = {};
    if (editForm.name.trim()) payload.name = editForm.name.trim();
    if (editForm.dept.trim()) payload.dept = editForm.dept.trim();
    if (editForm.year) payload.year = parseInt(editForm.year, 10);
    if (editForm.section.trim()) payload.section = editForm.section.trim();

    if (Object.keys(payload).length === 0) {
      toast.error("No changes to save");
      return;
    }
    try {
      setEditSaving(true);
      await api.patch("/profile/me", payload);
      toast.success("Profile updated");
      await refreshUser();
      setEditOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Update failed");
    } finally {
      setEditSaving(false);
    }
  };

  const uploadPic = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("file", file);

      await api.post("/profile/upload-pic", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      toast.success("Profile picture updated");
      await refreshUser();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const openPeople = async (type) => {
    if (!user?.id) return;

    try {
      setPeopleLoading(true);
      setPeopleOpen(true);
      setPeopleTitle(type === "followers" ? "Followers" : "Following");

      const url = type === "followers" ? `/follow/followers/${user.id}` : `/follow/following/${user.id}`;
      const res = await api.get(url);
      setPeople(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load list");
    } finally {
      setPeopleLoading(false);
    }
  };

  const picUrl = user?.profile_pic_url ? `${API_BASE_URL}${user.profile_pic_url}` : null;

  return (
    <Layout title="My Profile">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="panel-depth border border-black bg-white p-8">
          <div className="flex flex-col items-center gap-8 md:flex-row md:items-start">
            <div className="mx-auto md:mx-0">
              <div className="flex h-32 w-32 items-center justify-center border-2 border-black bg-gray-50 p-1">
                {picUrl ? (
                  <img src={picUrl} alt="Profile" className="h-full w-full border border-gray-200 object-cover" />
                ) : (
                  <span className="text-4xl font-black text-gray-300">{user?.name?.[0]?.toUpperCase() || "U"}</span>
                )}
              </div>

              <label className="mt-3 block cursor-pointer text-center">
                <span className="bg-black px-3 py-1 text-xs font-bold uppercase tracking-wide text-white transition hover:bg-neutral-800">
                  {uploading ? "Updating..." : "Change Photo"}
                </span>
                <input
                  type="file"
                  accept="image/png, image/jpeg, image/jpg, image/webp"
                  className="hidden"
                  onChange={uploadPic}
                />
              </label>
            </div>

            <div className="flex-1 text-center md:text-left">
              <div className="flex flex-col items-center justify-between gap-4 md:flex-row md:items-start">
                <div>
                  <h2 className="text-3xl font-black uppercase tracking-tighter text-black">{user?.name}</h2>
                  <p className="text-sm font-bold uppercase tracking-wide text-gray-500">{user?.email}</p>
                </div>

                <div className="flex items-center gap-2">
                  {user?.is_email_verified ? (
                    <span className="border border-black bg-black px-3 py-1 text-xs font-bold uppercase tracking-widest text-white">Verified</span>
                  ) : (
                    <span className="border border-black bg-yellow-400 px-3 py-1 text-xs font-bold uppercase tracking-widest text-black">Unverified</span>
                  )}
                  <button
                    onClick={openEdit}
                    className="btn-secondary text-xs px-3 py-1"
                  >
                    Edit
                  </button>
                </div>
              </div>

              <div className="mt-6 flex flex-col items-center gap-6 border-y border-gray-100 py-4 md:flex-row md:items-start">
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-gray-400">Department</label>
                  <p className="text-lg font-bold uppercase text-black">{user?.dept || "N/A"}</p>
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-gray-400">Year</label>
                  <p className="text-lg font-bold uppercase text-black">{user?.year || "N/A"}</p>
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase tracking-widest text-gray-400">Section</label>
                  <p className="text-lg font-bold uppercase text-black">{user?.section || "N/A"}</p>
                </div>
                {user?.verified_seller && (
                  <div>
                    <label className="block text-[10px] font-bold uppercase tracking-widest text-gray-400">Seller</label>
                    <p className="text-lg font-bold uppercase text-blue-700">Verified ✓</p>
                  </div>
                )}
              </div>

              <div className="mt-6 flex justify-center gap-4 md:justify-start">
                <button
                  onClick={() => openPeople("followers")}
                  className="min-w-[120px] border border-gray-200 bg-gray-50 px-6 py-3 transition-all hover:border-black hover:bg-white"
                >
                  <p className="text-xs font-bold uppercase tracking-wider text-gray-400">Followers</p>
                  <p className="text-2xl font-black text-black">{user?.followers_count ?? 0}</p>
                </button>

                <button
                  onClick={() => openPeople("following")}
                  className="min-w-[120px] border border-gray-200 bg-gray-50 px-6 py-3 transition-all hover:border-black hover:bg-white"
                >
                  <p className="text-xs font-bold uppercase tracking-wider text-gray-400">Following</p>
                  <p className="text-2xl font-black text-black">{user?.following_count ?? 0}</p>
                </button>

                {user?.wallet_points !== undefined && (
                  <div className="min-w-[120px] border border-gray-200 bg-gray-50 px-6 py-3">
                    <p className="text-xs font-bold uppercase tracking-wider text-gray-400">Wallet</p>
                    <p className="text-2xl font-black text-black">{user.wallet_points} pts</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Edit Profile Modal */}
        {editOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="w-full max-w-md border border-black bg-white">
              <div className="border-b border-black p-4 flex items-center justify-between">
                <h3 className="text-sm font-black uppercase tracking-wider text-black">Edit Profile</h3>
                <button
                  onClick={() => setEditOpen(false)}
                  className="text-zinc-500 hover:text-black font-bold text-lg leading-none"
                >
                  ✕
                </button>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-wider text-zinc-600 mb-1">
                    Full Name
                  </label>
                  <input
                    className="input-surface w-full"
                    placeholder="Your full name"
                    value={editForm.name}
                    onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))}
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-wider text-zinc-600 mb-1">
                    Department
                  </label>
                  <select
                    className="input-surface w-full"
                    value={editForm.dept}
                    onChange={(e) => setEditForm((p) => ({ ...p, dept: e.target.value }))}
                  >
                    <option value="">Select department</option>
                    {DEPT_OPTIONS.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-wider text-zinc-600 mb-1">
                      Year
                    </label>
                    <select
                      className="input-surface w-full"
                      value={editForm.year}
                      onChange={(e) => setEditForm((p) => ({ ...p, year: e.target.value }))}
                    >
                      <option value="">Select year</option>
                      {[1, 2, 3, 4].map((y) => (
                        <option key={y} value={y}>Year {y}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-wider text-zinc-600 mb-1">
                      Section
                    </label>
                    <input
                      className="input-surface w-full"
                      placeholder="e.g. A, B, C"
                      value={editForm.section}
                      onChange={(e) => setEditForm((p) => ({ ...p, section: e.target.value.toUpperCase() }))}
                      maxLength={3}
                    />
                  </div>
                </div>

                <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">
                  Note: Email and college cluster cannot be changed after verification.
                </p>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={saveProfile}
                    disabled={editSaving}
                    className="btn-primary flex-1 text-xs py-2 disabled:opacity-50"
                  >
                    {editSaving ? "Saving..." : "Save Changes"}
                  </button>
                  <button onClick={() => setEditOpen(false)} className="btn-secondary text-xs px-4">
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <PeopleModal
        open={peopleOpen}
        onClose={() => setPeopleOpen(false)}
        title={peopleTitle}
        loading={peopleLoading}
        people={people}
      />
    </Layout>
  );
}
