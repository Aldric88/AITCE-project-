import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import { apiCachedFetcher, useApiQuery } from "../api/useApiQuery";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import { API_BASE_URL } from "../api/baseUrl";

export default function Notifications() {
  const [list, setList] = useState([]);
  const [unread, setUnread] = useState(0);
  const [prefs, setPrefs] = useState({ realtime_enabled: true, digest_enabled: true, enabled_types: [] });
  const [digest, setDigest] = useState(null);

  const listQuery = useApiQuery(
    "notifications:list",
    apiCachedFetcher(ENDPOINTS.notifications.list),
    {
      staleTimeMs: 15000,
      refetchIntervalMs: 30000,
      onError: () => toast.error("Failed to load notifications"),
    },
  );
  const unreadQuery = useApiQuery(
    "notifications:unread",
    apiCachedFetcher(ENDPOINTS.notifications.unreadCount),
    {
      staleTimeMs: 10000,
      refetchIntervalMs: 30000,
    },
  );
  const prefsQuery = useApiQuery(
    "notifications:prefs",
    apiCachedFetcher(ENDPOINTS.notifications.preferences),
    { staleTimeMs: 30000 },
  );
  const digestQuery = useApiQuery(
    "notifications:digest",
    apiCachedFetcher(ENDPOINTS.notifications.digest),
    { staleTimeMs: 30000 },
  );
  const loading = listQuery.isLoading || unreadQuery.isLoading;

  useEffect(() => {
    let stream = null;
    if (window.EventSource) {
      stream = new EventSource(`${API_BASE_URL}${ENDPOINTS.notifications.stream}`, { withCredentials: true });
      stream.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data || "{}");
          if (typeof payload.unread === "number") setUnread(payload.unread);
          if (payload.latest?.id) {
            setList((prev) => {
              if (prev.find((x) => x.id === payload.latest.id)) return prev;
              return [
                {
                  id: payload.latest.id,
                  type: payload.latest.type || "general",
                  message: payload.latest.message || "New notification",
                  created_at: payload.latest.created_at || Math.floor(Date.now() / 1000),
                  is_read: false,
                },
                ...prev,
              ];
            });
          }
        } catch {
          // ignore malformed event payload
        }
      };
    }
    return () => {
      if (stream) stream.close();
    };
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (listQuery.data) setList(listQuery.data || []);
    if (unreadQuery.data) setUnread(unreadQuery.data?.unread || 0);
    if (prefsQuery.data) setPrefs(prefsQuery.data || {});
    if (digestQuery.data) setDigest(digestQuery.data || null);
  }, [listQuery.data, unreadQuery.data, prefsQuery.data, digestQuery.data]);

  const markAsRead = async (notificationId) => {
    try {
      await api.post(ENDPOINTS.notifications.readOne(notificationId));
      setList((prev) => prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n)));
      setUnread((u) => Math.max(0, u - 1));
    } catch {
      toast.error("Failed to mark as read");
    }
  };

  const markAllRead = async () => {
    try {
      await api.post(ENDPOINTS.notifications.readAll);
      setList((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnread(0);
      toast.success("All marked as read");
    } catch {
      toast.error("Failed to mark all as read");
    }
  };

  const updatePrefs = async (next) => {
    setPrefs(next);
    try {
      await api.patch(ENDPOINTS.notifications.preferences, next);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to update preferences");
    }
  };

  return (
    <Layout title="Notifications">
      <div className="mx-auto max-w-3xl">
        <div className="panel-depth border border-black bg-white p-8">
          <div className="mb-8 flex items-center justify-between border-b-2 border-black pb-4">
            <h2 className="text-2xl font-black uppercase tracking-tighter text-black">Notifications ({unread} unread)</h2>
            <button
              onClick={markAllRead}
              className="border border-black px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-black transition hover:bg-black hover:text-white"
            >
              Mark All Read
            </button>
          </div>

          <div className="mb-6 grid grid-cols-1 gap-3 border border-zinc-200 p-3 md:grid-cols-3">
            <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-zinc-600">
              <input
                type="checkbox"
                checked={!!prefs.realtime_enabled}
                onChange={(e) => updatePrefs({ ...prefs, realtime_enabled: e.target.checked })}
              />
              Realtime
            </label>
            <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-zinc-600">
              <input
                type="checkbox"
                checked={!!prefs.digest_enabled}
                onChange={(e) => updatePrefs({ ...prefs, digest_enabled: e.target.checked })}
              />
              Digest
            </label>
            <button
              onClick={() => digestQuery.refetch()}
              className="btn-secondary text-xs"
            >
              Refresh Digest
            </button>
          </div>

          {digest && (
            <div className="mb-6 border border-zinc-200 p-4">
              <p className="mb-2 text-xs font-black uppercase tracking-[0.2em] text-zinc-600">24h Digest ({digest.total || 0})</p>
              <div className="flex flex-wrap gap-2">
                {(digest.by_type || []).map((d) => (
                  <span key={d.type} className="border border-zinc-200 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-zinc-700">
                    {d.type}: {d.count}
                  </span>
                ))}
              </div>
            </div>
          )}

          {loading ? (
            <Spinner label="Loading notifications..." />
          ) : list.length === 0 ? (
            <div className="border-2 border-dashed border-gray-200 bg-gray-50 py-12 text-center">
              <p className="text-xs font-bold uppercase text-gray-500">No notifications yet</p>
            </div>
          ) : (
            <div className="space-y-3">
              {list.map((n) => (
                <div
                  key={n.id}
                  className={`cursor-pointer border p-4 transition-all duration-200 ${
                    n.is_read
                      ? "border-gray-200 bg-white hover:border-black"
                      : "-translate-x-1 -translate-y-1 border-black bg-gray-50 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-0 hover:translate-y-0 hover:bg-white hover:shadow-none"
                  }`}
                  onClick={() => !n.is_read && markAsRead(n.id)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className={`text-sm ${n.is_read ? "font-medium text-gray-600" : "font-bold uppercase tracking-wide text-black"}`}>
                        {n.message}
                      </p>
                      <p className="mt-2 inline-block border-t border-gray-100 pt-2 text-[10px] font-bold uppercase tracking-widest text-gray-400">
                        {new Date(n.created_at * 1000).toLocaleString()}
                      </p>
                    </div>
                    {!n.is_read && <div className="mt-2 h-2 w-2 shrink-0 bg-black" />}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
