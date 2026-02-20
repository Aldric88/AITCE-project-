import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../api/axios";
import { API_BASE_URL } from "../api/baseUrl";
import toast from "react-hot-toast";

export default function SecureViewer() {
  const { noteId } = useParams();
  const [viewerUrl, setViewerUrl] = useState("");
  const [loading, setLoading] = useState(true);

  const startSession = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.post(`/secure/session/start/${noteId}`);
      setViewerUrl(`${API_BASE_URL}${res.data.viewer_url}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Unable to start secure session");
    } finally {
      setLoading(false);
    }
  }, [noteId]);

  useEffect(() => {
    startSession();
  }, [startSession]);

  useEffect(() => {
    const blockContext = (e) => e.preventDefault();
    const blockKeys = (e) => {
      const key = e.key?.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && ["p", "c", "s"].includes(key)) {
        e.preventDefault();
        toast.error("Action disabled");
      }
    };

    document.addEventListener("contextmenu", blockContext);
    document.addEventListener("keydown", blockKeys);

    return () => {
      document.removeEventListener("contextmenu", blockContext);
      document.removeEventListener("keydown", blockKeys);
    };
  }, []);

  return (
    <Layout title="Secure Viewer">
      <div className="mx-auto max-w-5xl">
        <div className="panel-depth border border-black bg-white p-4">
          {loading ? (
            <p className="animate-pulse text-sm font-bold uppercase text-black">Starting secure session...</p>
          ) : !viewerUrl ? (
            <div className="border border-dashed border-gray-300 bg-gray-50 py-12 text-center">
              <p className="text-sm font-bold uppercase text-gray-400">Unable to load note.</p>
            </div>
          ) : (
            <div className="border border-black bg-gray-100">
              <iframe src={viewerUrl} title="Secure PDF Viewer" className="w-full" style={{ height: "85vh" }} />
            </div>
          )}

          <p className="mt-4 border-t border-gray-200 pt-2 text-[10px] font-bold uppercase tracking-widest text-gray-400">
            Note: Screenshot protection is best-effort. Watermark is embedded.
          </p>
        </div>
      </div>
    </Layout>
  );
}
