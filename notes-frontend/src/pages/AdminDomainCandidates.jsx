import { useCallback, useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import toast from "react-hot-toast";

const DEFAULT_TYPE = "anna_affiliated";

export default function AdminDomainCandidates() {
  const { user } = useAuth();
  const [reviewStatus, setReviewStatus] = useState("pending");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [drafts, setDrafts] = useState({});
  const [busyDomain, setBusyDomain] = useState("");

  const canView = user?.role === "admin";

  const load = useCallback(async () => {
    if (!canView) return;
    setLoading(true);
    try {
      const res = await api.get(`${ENDPOINTS.admin.domainCandidates}?review_status=${reviewStatus}&limit=100`);
      const items = res.data?.items || [];
      setRows(items);
      setDrafts((prev) => {
        const next = { ...prev };
        for (const item of items) {
          if (!next[item.domain]) {
            next[item.domain] = {
              college_name: guessCollegeName(item.domain),
              university_type: item.last_inferred_university_type || DEFAULT_TYPE,
            };
          }
        }
        return next;
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load domain candidates");
    } finally {
      setLoading(false);
    }
  }, [canView, reviewStatus]);

  useEffect(() => {
    load();
  }, [load]);

  const pendingCount = useMemo(
    () => rows.filter((r) => r.review_status === "pending").length,
    [rows],
  );

  const updateDraft = (domain, key, value) => {
    setDrafts((prev) => ({
      ...prev,
      [domain]: { ...(prev[domain] || {}), [key]: value },
    }));
  };

  const approve = async (domain) => {
    const draft = drafts[domain] || {};
    if (!draft.college_name?.trim()) {
      toast.error("College name is required");
      return;
    }

    setBusyDomain(domain);
    try {
      await api.post(ENDPOINTS.admin.approveDomainCandidate(domain), {
        college_name: draft.college_name.trim(),
        university_type: draft.university_type || DEFAULT_TYPE,
      });
      toast.success(`Approved ${domain}`);
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Approve failed");
    } finally {
      setBusyDomain("");
    }
  };

  const reject = async (domain) => {
    setBusyDomain(domain);
    try {
      await api.post(ENDPOINTS.admin.rejectDomainCandidate(domain), {
        reason: "Rejected by admin",
      });
      toast.success(`Rejected ${domain}`);
      await load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Reject failed");
    } finally {
      setBusyDomain("");
    }
  };

  if (!canView) {
    return (
      <Layout title="Domain Candidates">
        <div className="border border-red-300 bg-red-50 p-8">
          <h2 className="text-sm font-black uppercase tracking-wider text-red-700">Admin access required</h2>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Domain Candidates">
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <select
          className="input-surface max-w-xs"
          value={reviewStatus}
          onChange={(e) => setReviewStatus(e.target.value)}
        >
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="all">All</option>
        </select>
        <button onClick={load} className="btn-primary px-4 text-xs">Refresh</button>
        <span className="text-xs font-bold uppercase tracking-wider text-zinc-500">
          Showing {rows.length} • Pending {pendingCount}
        </span>
      </div>

      {loading ? (
        <div className="border border-black bg-white p-6 text-sm text-zinc-500">Loading...</div>
      ) : rows.length === 0 ? (
        <div className="border border-black bg-white p-6 text-sm text-zinc-500">No candidates found.</div>
      ) : (
        <div className="space-y-4">
          {rows.map((item) => {
            const draft = drafts[item.domain] || {};
            const isPending = item.review_status === "pending";
            const isBusy = busyDomain === item.domain;
            return (
              <div key={item.id} className="border border-black bg-white p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-black uppercase tracking-wide text-black">{item.domain}</p>
                  <span className="border border-zinc-300 px-2 py-1 text-[10px] font-bold uppercase text-zinc-600">
                    {item.review_status}
                  </span>
                </div>

                <div className="mb-4 grid grid-cols-1 gap-2 text-xs text-zinc-600 md:grid-cols-4">
                  <p><span className="font-bold text-zinc-800">Inferred:</span> {item.last_inferred_university_type || "-"}</p>
                  <p><span className="font-bold text-zinc-800">Confidence:</span> {item.last_confidence ?? "-"}</p>
                  <p><span className="font-bold text-zinc-800">Source:</span> {item.last_source || "-"}</p>
                  <p><span className="font-bold text-zinc-800">Hits:</span> {item.inference_count}</p>
                </div>

                {isPending && (
                  <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    <input
                      value={draft.college_name || ""}
                      onChange={(e) => updateDraft(item.domain, "college_name", e.target.value)}
                      placeholder="College name"
                      className="input-surface"
                    />
                    <select
                      value={draft.university_type || DEFAULT_TYPE}
                      onChange={(e) => updateDraft(item.domain, "university_type", e.target.value)}
                      className="input-surface"
                    >
                      <option value="anna_affiliated">Anna Affiliated</option>
                      <option value="autonomous">Autonomous</option>
                      <option value="deemed">Deemed</option>
                    </select>
                    <div className="flex gap-2">
                      <button
                        disabled={isBusy}
                        onClick={() => approve(item.domain)}
                        className="btn-primary px-4 text-xs"
                      >
                        Approve
                      </button>
                      <button
                        disabled={isBusy}
                        onClick={() => reject(item.domain)}
                        className="border border-black px-4 text-xs font-bold uppercase tracking-wide text-black transition-colors hover:bg-black hover:text-white"
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Layout>
  );
}

function guessCollegeName(domain) {
  const first = (domain || "").split(".")[0] || "";
  return first
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase()) || "";
}

