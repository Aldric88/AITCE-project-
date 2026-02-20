import { useCallback, useEffect, useState } from "react";
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

  const loadSecureFile = useCallback(async () => {
    if (!note?.id) return;

    try {
      setLoading(true);
      const res = await api.get(`/secure/note/${note.id}/file`, { responseType: "blob" });
      const blobUrl = URL.createObjectURL(res.data);
      setFileBlobUrl(blobUrl);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load secure file");
    } finally {
      setLoading(false);
    }
  }, [note?.id]);

  useEffect(() => {
    const disableRightClick = (e) => e.preventDefault();
    document.addEventListener("contextmenu", disableRightClick);
    return () => document.removeEventListener("contextmenu", disableRightClick);
  }, []);

  useEffect(() => {
    loadSecureFile();
  }, [loadSecureFile]);

  useEffect(() => {
    return () => {
      if (fileBlobUrl) URL.revokeObjectURL(fileBlobUrl);
    };
  }, [fileBlobUrl]);

  if (!note) {
    return (
      <Layout title="Viewer">
        <p className="text-gray-500">Note not found.</p>
      </Layout>
    );
  }

  const watermarkText = `${user?.name || "User"} • ${user?.email || ""}`;

  return (
    <Layout title="Secure Viewer">
      <div className="relative overflow-hidden border border-black bg-white p-6">
        <h2 className="text-2xl font-semibold text-black">{note.title}</h2>

        <div className="pointer-events-none absolute right-6 top-6 text-sm opacity-20">{watermarkText}</div>

        {loading ? (
          <div className="mt-4">
            <Spinner label="Loading secure note..." />
          </div>
        ) : fileBlobUrl ? (
          <div className="relative mt-4 w-full overflow-hidden border border-black bg-gray-100">
            <iframe src={fileBlobUrl} width="100%" height="650px" className="bg-gray-100" title="Secure Viewer" />

            <div className="pointer-events-none absolute inset-0 opacity-15">
              <div className="flex h-full w-full items-center justify-center">
                <p
                  className="rotate-[-25deg] select-none text-6xl font-bold text-white"
                  style={{ whiteSpace: "pre-line", textAlign: "center" }}
                >
                  {user?.name}\n{user?.email}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-gray-500">Unable to load file.</p>
        )}

        <p className="mt-3 text-xs text-gray-500">File is streamed securely using JWT. Direct URL access is blocked.</p>
      </div>
    </Layout>
  );
}
