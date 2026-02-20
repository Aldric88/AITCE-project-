import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";

const INITIAL_FORM = {
  title: "",
  dept: "CSE",
  semester: 3,
  subject: "",
  unit: "1",
  description: "",
};

export default function Requests() {
  const [list, setList] = useState([]);
  const [heatmap, setHeatmap] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const { user } = useAuth();

  useEffect(() => {
    let active = true;

    const run = async () => {
      try {
        const [res, insightRes] = await Promise.all([
          api.get(ENDPOINTS.requests.list),
          api.get(ENDPOINTS.requests.heatmap),
        ]);
        if (active) {
          setList(res.data);
          setHeatmap(insightRes.data);
        }
      } catch {
        toast.error("Failed to load requests");
      }
    };

    run();
    return () => {
      active = false;
    };
  }, []);

  const reloadRequests = async () => {
    try {
      const [res, insightRes] = await Promise.all([
        api.get(ENDPOINTS.requests.list),
        api.get(ENDPOINTS.requests.heatmap),
      ]);
      setList(res.data);
      setHeatmap(insightRes.data);
    } catch {
      toast.error("Failed to refresh requests");
    }
  };

  const submit = async () => {
    try {
      if (!form.title.trim() || !form.subject.trim()) {
        toast.error("Title and subject are required");
        return;
      }

      await api.post(ENDPOINTS.requests.create, form);
      toast.success("Request posted");
      setForm((prev) => ({ ...prev, title: "", subject: "", description: "" }));
      reloadRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to post request");
    }
  };

  const closeRequest = async (requestId) => {
    try {
      await api.patch(ENDPOINTS.requests.close(requestId));
      toast.success("Request closed");
      reloadRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to close request");
    }
  };

  const voteRequest = async (requestId) => {
    try {
      const res = await api.post(ENDPOINTS.requests.vote(requestId));
      toast.success(res.data?.voted ? "Vote added" : "Vote removed");
      reloadRequests();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to vote");
    }
  };

  return (
    <Layout title="Note Requests">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="border border-black bg-white p-6">
          <h2 className="mb-6 text-xl font-bold uppercase tracking-wide text-black">Create Request</h2>

          <div className="space-y-4">
            <input
              className="input-surface"
              placeholder="Title"
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
            />

            <div className="grid grid-cols-2 gap-3">
              <select
                className="input-surface"
                value={form.dept}
                onChange={(e) => setForm((prev) => ({ ...prev, dept: e.target.value }))}
              >
                <option value="CSE">CSE</option>
                <option value="ECE">ECE</option>
                <option value="MECH">MECH</option>
                <option value="CIVIL">CIVIL</option>
                <option value="EEE">EEE</option>
              </select>

              <select
                className="input-surface"
                value={form.semester}
                onChange={(e) => setForm((prev) => ({ ...prev, semester: parseInt(e.target.value, 10) }))}
              >
                <option value={1}>Sem 1</option>
                <option value={2}>Sem 2</option>
                <option value={3}>Sem 3</option>
                <option value={4}>Sem 4</option>
                <option value={5}>Sem 5</option>
                <option value={6}>Sem 6</option>
                <option value={7}>Sem 7</option>
                <option value={8}>Sem 8</option>
              </select>
            </div>

            <input
              className="input-surface"
              placeholder="Subject"
              value={form.subject}
              onChange={(e) => setForm((prev) => ({ ...prev, subject: e.target.value }))}
            />

            <select
              className="input-surface"
              value={form.unit}
              onChange={(e) => setForm((prev) => ({ ...prev, unit: e.target.value }))}
            >
              <option value="1">Unit 1</option>
              <option value="2">Unit 2</option>
              <option value="3">Unit 3</option>
              <option value="4">Unit 4</option>
              <option value="5">Unit 5</option>
              <option value="6">Unit 6</option>
            </select>

            <textarea
              className="input-surface"
              placeholder="Description (optional)"
              value={form.description}
              onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
              rows={4}
            />

            <button onClick={submit} className="btn-primary w-full">
              Post Request
            </button>
          </div>
        </div>

        <div className="border border-black bg-white p-6">
          <h2 className="mb-6 text-xl font-bold uppercase tracking-wide text-black">Open Requests</h2>

          {list.length === 0 ? (
            <div className="py-12 text-center">
              <h3 className="mb-2 text-lg font-semibold text-zinc-800">No Requests Yet</h3>
              <p className="text-sm text-zinc-500">Be the first to request a note.</p>
            </div>
          ) : (
            <div className="max-h-[600px] space-y-4 overflow-y-auto">
              {list.map((r) => (
                <div key={r.id} className="border border-zinc-200 bg-white p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-zinc-900">{r.title}</h3>
                      <p className="mt-1 text-xs font-bold uppercase tracking-wide text-zinc-500">
                        {r.dept} • Sem {r.semester} • {r.subject} • Unit {r.unit}
                      </p>
                      {r.description && <p className="mt-2 text-sm text-zinc-600">{r.description}</p>}
                    </div>

                    {(user?.id === r.created_by || user?.role === "admin") && (
                      <button onClick={() => closeRequest(r.id)} className="btn-secondary border-red-300 text-red-700 hover:bg-red-50 text-xs px-3 py-1">
                        Close
                      </button>
                    )}
                  </div>
                  <div className="mt-3 flex items-center justify-between border-t border-zinc-100 pt-3">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">Votes: {r.vote_count || 0}</span>
                    <button onClick={() => voteRequest(r.id)} className="btn-secondary text-xs px-3 py-1">
                      Vote
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 border border-black bg-white p-6">
        <h2 className="mb-4 text-lg font-black uppercase tracking-wide text-black">Demand Heatmap</h2>
        {!heatmap ? (
          <p className="text-sm text-zinc-500">No demand data yet.</p>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <div>
              <p className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-500">Top Subjects</p>
              <div className="space-y-2">
                {(heatmap.top_subjects || []).slice(0, 8).map((s) => (
                  <div key={s.subject} className="flex items-center justify-between border border-zinc-200 px-3 py-2 text-xs">
                    <span className="font-bold text-zinc-700">{s.subject}</span>
                    <span className="font-black text-black">{s.count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-500">Top Units</p>
              <div className="space-y-2">
                {(heatmap.top_units || []).slice(0, 8).map((u) => (
                  <div key={u.unit} className="flex items-center justify-between border border-zinc-200 px-3 py-2 text-xs">
                    <span className="font-bold text-zinc-700">Unit {u.unit}</span>
                    <span className="font-black text-black">{u.count}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-500">Most Voted Requests</p>
              <div className="space-y-2">
                {(heatmap.top_requests || []).slice(0, 8).map((r) => (
                  <div key={r.id} className="border border-zinc-200 px-3 py-2">
                    <p className="text-xs font-bold text-zinc-800">{r.title}</p>
                    <p className="text-[10px] font-bold uppercase text-zinc-500">{r.subject} • Unit {r.unit} • {r.dept}</p>
                    <p className="mt-1 text-[10px] font-black uppercase text-black">{r.vote_count || 0} votes</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
