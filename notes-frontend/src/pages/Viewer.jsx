import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../auth/AuthContext";
import api from "../api/axios";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";

export default function Viewer() {
  const { user } = useAuth();
  const location = useLocation();
  const note = location.state?.note;

  const [fileBlobUrl, setFileBlobUrl] = useState("");
  const [loading, setLoading] = useState(true);

  const loadSecureFile = async () => {
    try {
      setLoading(true);

      const res = await api.get(`/secure/note/${note.id}/file`, {
        responseType: "blob",
      });

      const blobUrl = URL.createObjectURL(res.data);
      setFileBlobUrl(blobUrl);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load secure file");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const disableRightClick = (e) => e.preventDefault();
    document.addEventListener("contextmenu", disableRightClick);
    return () => document.removeEventListener("contextmenu", disableRightClick);
  }, []);

  useEffect(() => {
    if (note?.id) loadSecureFile();
  }, [note?.id]);

  if (!note) {
    return (
      <Layout title="Viewer">
        <p className="text-zinc-400">Note not found.</p>
      </Layout>
    );
  }

  const watermarkText = `${user?.name || "User"} • ${user?.email || ""}`;

  return (
    <Layout title="Secure Viewer">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 relative overflow-hidden">
        <h2 className="text-2xl font-semibold">{note.title}</h2>

        {/* watermark */}
        <div className="absolute top-6 right-6 opacity-20 text-sm pointer-events-none select-none">
          {watermarkText}
        </div>

        {loading ? (
          <div className="mt-4">
            <Spinner label="Loading secure note..." />
          </div>
        ) : fileBlobUrl ? (
          <div className="mt-4 rounded-xl overflow-hidden border border-zinc-800">
            <iframe
              src={fileBlobUrl}
              width="100%"
              height="650px"
              className="bg-zinc-950"
              title="Note Viewer"
            />
          </div>
        ) : (
          <p className="text-zinc-400 mt-4">Unable to load file.</p>
        )}

        <p className="text-xs text-zinc-500 mt-3">
          ✅ This file is streamed securely using JWT. Direct URL access is blocked.
        </p>
      </div>
    </Layout>
  );
}
