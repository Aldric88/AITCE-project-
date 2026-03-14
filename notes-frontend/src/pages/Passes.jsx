import { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import toast from "react-hot-toast";

const INITIAL_PASS_FORM = {
  title: "",
  description: "",
  monthly_price: 100,
  duration_days: 30,
  max_subscribers: "",
};

export default function Passes() {
  const [myPasses, setMyPasses] = useState([]);
  const [available, setAvailable] = useState([]);
  const [mySubscriptions, setMySubscriptions] = useState([]);
  const [passForm, setPassForm] = useState(INITIAL_PASS_FORM);
  const [tab, setTab] = useState("browse"); // browse | my-passes | subscriptions | create

  const loadAll = useCallback(async () => {
    try {
      const [availRes, myRes, subsRes] = await Promise.all([
        api.get(ENDPOINTS.monetization.passesAvailable),
        api.get(ENDPOINTS.monetization.passesMine),
        api.get(ENDPOINTS.monetization.passSubscriptionsMine),
      ]);
      setAvailable(availRes.data || []);
      setMyPasses(myRes.data || []);
      setMySubscriptions(subsRes.data || []);
    } catch {
      toast.error("Failed to load passes");
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const createPass = async () => {
    if (!passForm.title.trim()) {
      toast.error("Title is required");
      return;
    }
    try {
      await api.post(ENDPOINTS.monetization.passesCreate, {
        ...passForm,
        monthly_price: parseInt(passForm.monthly_price, 10) || 100,
        duration_days: parseInt(passForm.duration_days, 10) || 30,
        max_subscribers: passForm.max_subscribers ? parseInt(passForm.max_subscribers, 10) : undefined,
      });
      toast.success("Creator pass created");
      setPassForm(INITIAL_PASS_FORM);
      setTab("my-passes");
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create pass");
    }
  };

  const subscribe = async (passId, passTitle) => {
    try {
      const res = await api.post(ENDPOINTS.monetization.passSubscribe(passId), { payment_method: "points" });
      toast.success(`Subscribed to "${passTitle}" — ${res.data.spent_points} pts spent`);
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to subscribe");
    }
  };

  const tabs = [
    { id: "browse", label: "Browse Passes" },
    { id: "subscriptions", label: "My Subscriptions" },
    { id: "my-passes", label: "My Passes" },
    { id: "create", label: "Create Pass" },
  ];

  return (
    <Layout title="Creator Passes">
      <div className="mb-6 flex flex-wrap gap-2 border-b border-zinc-200 pb-4">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-xs font-black uppercase tracking-wider border ${
              tab === t.id
                ? "border-black bg-black text-white"
                : "border-zinc-300 bg-white text-zinc-700 hover:border-black"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "browse" && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {available.length === 0 ? (
            <p className="text-sm text-zinc-500">No passes available right now.</p>
          ) : (
            available.map((p) => (
              <div key={p.id} className="border border-black bg-white p-5">
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">{p.seller_name}</p>
                <h3 className="mt-1 text-base font-black uppercase tracking-tight text-black">{p.title}</h3>
                {p.description && <p className="mt-1 text-xs text-zinc-600">{p.description}</p>}
                <div className="mt-3 flex items-center justify-between border-t border-zinc-100 pt-3">
                  <div>
                    <p className="text-lg font-black text-black">{p.monthly_price} pts</p>
                    <p className="text-[10px] font-bold uppercase text-zinc-500">{p.duration_days} days • {p.active_subscriptions} subscribers</p>
                  </div>
                  <button
                    onClick={() => subscribe(p.id, p.title)}
                    className="btn-primary px-4 py-2 text-xs"
                  >
                    Subscribe
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "subscriptions" && (
        <div className="space-y-3">
          {mySubscriptions.length === 0 ? (
            <p className="text-sm text-zinc-500">No active subscriptions.</p>
          ) : (
            mySubscriptions.map((s) => (
              <div key={s.id} className="flex items-center justify-between border border-zinc-200 bg-white p-4">
                <div>
                  <p className="text-sm font-black uppercase text-zinc-800">{s.title}</p>
                  <p className="text-[10px] font-bold uppercase text-zinc-500">{s.seller_name}</p>
                  <p className="mt-1 text-xs text-zinc-600">
                    Expires: {s.expires_at ? new Date(s.expires_at * 1000).toLocaleDateString() : "—"}
                  </p>
                </div>
                <span
                  className={`px-3 py-1 text-[10px] font-black uppercase tracking-wider ${
                    s.is_active ? "bg-green-100 text-green-800" : "bg-zinc-100 text-zinc-600"
                  }`}
                >
                  {s.is_active ? "Active" : "Expired"}
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "my-passes" && (
        <div className="space-y-3">
          {myPasses.length === 0 ? (
            <p className="text-sm text-zinc-500">You haven't created any passes yet.</p>
          ) : (
            myPasses.map((p) => (
              <div key={p.id} className="flex items-center justify-between border border-zinc-200 bg-white p-4">
                <div>
                  <p className="text-sm font-black uppercase text-zinc-800">{p.title}</p>
                  {p.description && <p className="text-xs text-zinc-500">{p.description}</p>}
                  <p className="mt-1 text-[10px] font-bold uppercase text-zinc-500">
                    {p.monthly_price} pts / {p.duration_days} days • {p.active_subscriptions} active subs
                  </p>
                </div>
                <span className={`px-3 py-1 text-[10px] font-black uppercase ${p.is_active ? "bg-green-100 text-green-800" : "bg-zinc-100 text-zinc-500"}`}>
                  {p.is_active ? "Active" : "Inactive"}
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {tab === "create" && (
        <div className="max-w-md border border-black bg-white p-6">
          <h3 className="mb-4 text-sm font-black uppercase tracking-wider">Create Creator Pass</h3>
          <div className="space-y-3">
            <input
              className="input-surface"
              placeholder="Pass Title"
              value={passForm.title}
              onChange={(e) => setPassForm((p) => ({ ...p, title: e.target.value }))}
            />
            <textarea
              className="input-surface"
              placeholder="Description (optional)"
              value={passForm.description}
              onChange={(e) => setPassForm((p) => ({ ...p, description: e.target.value }))}
              rows={3}
            />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-[10px] font-black uppercase tracking-wider text-zinc-500">Price (Points)</label>
                <input
                  className="input-surface"
                  type="number"
                  min={1}
                  max={5000}
                  value={passForm.monthly_price}
                  onChange={(e) => setPassForm((p) => ({ ...p, monthly_price: e.target.value }))}
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-black uppercase tracking-wider text-zinc-500">Duration (Days)</label>
                <input
                  className="input-surface"
                  type="number"
                  min={7}
                  max={365}
                  value={passForm.duration_days}
                  onChange={(e) => setPassForm((p) => ({ ...p, duration_days: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-black uppercase tracking-wider text-zinc-500">Max Subscribers (optional)</label>
              <input
                className="input-surface"
                type="number"
                min={1}
                placeholder="Unlimited"
                value={passForm.max_subscribers}
                onChange={(e) => setPassForm((p) => ({ ...p, max_subscribers: e.target.value }))}
              />
            </div>
            <button onClick={createPass} className="btn-primary w-full">
              Create Pass
            </button>
          </div>
        </div>
      )}
    </Layout>
  );
}
