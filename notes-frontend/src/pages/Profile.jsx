import { useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { API_BASE_URL } from "../api/baseUrl";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";
import PeopleModal from "../components/PeopleModal";

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [peopleOpen, setPeopleOpen] = useState(false);
  const [peopleTitle, setPeopleTitle] = useState("");
  const [people, setPeople] = useState([]);
  const [peopleLoading, setPeopleLoading] = useState(false);

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
      <div className="mx-auto max-w-3xl">
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

                <div>
                  {user?.is_email_verified ? (
                    <span className="border border-black bg-black px-3 py-1 text-xs font-bold uppercase tracking-widest text-white">Verified</span>
                  ) : (
                    <span className="border border-black bg-yellow-400 px-3 py-1 text-xs font-bold uppercase tracking-widest text-black">Unverified</span>
                  )}
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
              </div>
            </div>
          </div>
        </div>
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
