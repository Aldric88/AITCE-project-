import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import Spinner from "../components/Spinner";
import { showAiResultToast } from "../utils/aiFeedback.jsx";

export default function ModerationDashboard() {
  const [tab, setTab] = useState("pending"); // pending / rejected / approved

  const [pending, setPending] = useState([]);
  const [rejected, setRejected] = useState([]);
  const [approved, setApproved] = useState([]);

  const [loading, setLoading] = useState(true);

  const [selected, setSelected] = useState(null);
  const [open, setOpen] = useState(false);

  const [previewUrl, setPreviewUrl] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);

  const [rejectReason, setRejectReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [queueInfo, setQueueInfo] = useState({ count: 0, top: [] });
  const [analytics, setAnalytics] = useState(null);
  const [rules, setRules] = useState(null);
  const [rulesSaving, setRulesSaving] = useState(false);
  const [appeals, setAppeals] = useState([]);
  const [confidenceTrend, setConfidenceTrend] = useState([]);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insights, setInsights] = useState({
    explain: null,
    quality: null,
    duplicates: [],
    suggestedTags: [],
    timeline: [],
    trust: null,
    diff: null,
  });

  const loadPreview = async (noteId) => {
    try {
      setPreviewLoading(true);
      const res = await api.get(`/secure/note/${noteId}/file`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(res.data);
      setPreviewUrl(url);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Preview load failed");
    } finally {
      setPreviewLoading(false);
    }
  };

  const fetchAll = async () => {
    try {
      setLoading(true);
      const [p, r, a, q, an, rl, ap, ct] = await Promise.allSettled([
        api.get("/notes/pending"),
        api.get("/notes/rejected"),
        api.get("/notes/approved"),
        api.get("/moderation/features/queue?limit=5"),
        api.get("/moderation/features/analytics?days=30"),
        api.get("/moderation/features/rules"),
        api.get("/moderation/features/appeals?status=open"),
        api.get("/moderation/features/confidence-trend?days=14"),
      ]);

      if (p.status === "fulfilled") setPending(p.value.data || []);
      if (r.status === "fulfilled") setRejected(r.value.data || []);
      if (a.status === "fulfilled") setApproved(a.value.data || []);
      if (q.status === "fulfilled") {
        setQueueInfo({ count: q.value.data.count || 0, top: q.value.data.items || [] });
      }
      if (an.status === "fulfilled") setAnalytics(an.value.data || null);
      if (rl.status === "fulfilled") setRules(rl.value.data || null);
      if (ap.status === "fulfilled") setAppeals(ap.value.data || []);
      if (ct.status === "fulfilled") setConfidenceTrend(ct.value.data?.points || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load moderation data");
    } finally {
      setLoading(false);
    }
  };

  const runAI = async (noteId) => {
    try {
      toast.loading("Running AI...", { id: `ai-${noteId}` });
      const res = await api.post(`/ai/analyze-note/${noteId}`);

      const { validation_success, validation_message, critical_issues, report, metadata } = res.data;
      toast.dismiss(`ai-${noteId}`);
      showAiResultToast({
        validation_success,
        validation_message,
        critical_issues,
        moderation_bucket: res.data.moderation_bucket,
        provider: res.data.provider,
        cached_reuse: res.data.cached_reuse,
      });

      // refresh current data
      await fetchAll();

      if (selected?.id === noteId) {
        const merged = {
          ...selected,
          ai: {
            ...res.data,
            validation_success,
            validation_message,
            critical_issues,
            report,
            metadata
          }
        };
        setSelected((prev) => ({ 
          ...prev, 
          ai: {
            ...res.data,
            validation_success,
            validation_message,
            critical_issues,
            report,
            metadata
          }
        }));
        await loadInsights(merged);
      }
    } catch (err) {
      toast.dismiss(`ai-${noteId}`);
      showAiResultToast({
        validation_success: false,
        validation_message: err.response?.data?.detail || "AI failed",
        critical_issues: ["Analysis request failed. Please retry."],
        moderation_bucket: "needs_moderator_review",
        provider: "error",
      });
    }
  };

  const approveNote = async (noteId) => {
    try {
      setActionLoading(true);
      await api.patch(`/notes/${noteId}/approve`);
      toast.success("Approved ✅");
      setOpen(false);
      setSelected(null);
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Approve failed");
    } finally {
      setActionLoading(false);
    }
  };

  const rejectNote = async (noteId) => {
    try {
      if (rejectReason.trim().length < 3) {
        toast.error("Enter reject reason (min 3 chars)");
        return;
      }

      setActionLoading(true);
      await api.patch(`/notes/${noteId}/reject`, { reason: rejectReason });
      toast.success("Rejected ❌");
      setRejectReason("");
      setOpen(false);
      setSelected(null);
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Reject failed");
    } finally {
      setActionLoading(false);
    }
  };

  // ✅ Override approve rejected
  const overrideApprove = async (noteId) => {
    try {
      setActionLoading(true);
      await api.patch(`/notes/${noteId}/override-approve`);
      toast.success("Override Approved ✅");
      setOpen(false);
      setSelected(null);
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Override approve failed");
    } finally {
      setActionLoading(false);
    }
  };

  // ✅ Override reject approved
  const overrideReject = async (noteId) => {
    try {
      if (rejectReason.trim().length < 3) {
        toast.error("Enter reject reason (min 3 chars)");
        return;
      }

      setActionLoading(true);
      await api.patch(`/notes/${noteId}/override-reject`, { reason: rejectReason });
      toast.success("Override Rejected ❌");
      setRejectReason("");
      setOpen(false);
      setSelected(null);
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Override reject failed");
    } finally {
      setActionLoading(false);
    }
  };

  const openNote = async (note) => {
    setSelected(note);
    setOpen(true);
    setRejectReason("");
    setPreviewUrl("");
    await Promise.all([loadPreview(note.id), loadInsights(note)]);
  };

  const loadInsights = async (note) => {
    try {
      setInsightsLoading(true);
      const requests = [
        api.get(`/moderation/features/explain/${note.id}`),
        api.get(`/moderation/features/quality-gate/check/${note.id}`),
        api.get(`/moderation/features/duplicates/${note.id}`),
        api.post(`/moderation/features/suggest-tags/${note.id}`),
        api.get(`/moderation/features/timeline/${note.id}`),
        api.get(`/moderation/features/diff/${note.id}`),
      ];
      if (note.uploader_id) {
        requests.push(api.get(`/moderation/features/creator-trust/${note.uploader_id}`));
      }
      const [explain, quality, duplicates, tags, timeline, diff, trust] = await Promise.allSettled(requests);
      setInsights({
        explain: explain.status === "fulfilled" ? explain.value.data : null,
        quality: quality.status === "fulfilled" ? quality.value.data : null,
        duplicates: duplicates.status === "fulfilled" ? duplicates.value.data?.duplicates || [] : [],
        suggestedTags: tags.status === "fulfilled" ? tags.value.data?.suggested_tags || [] : [],
        timeline: timeline.status === "fulfilled" ? timeline.value.data?.events || [] : [],
        diff: diff.status === "fulfilled" ? diff.value.data : null,
        trust: trust?.status === "fulfilled" ? trust.value.data : null,
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load moderation insights");
    } finally {
      setInsightsLoading(false);
    }
  };

  const saveRules = async () => {
    if (!rules) return;
    try {
      setRulesSaving(true);
      await api.patch("/moderation/features/rules", {
        auto_approve_max_risk: Number(rules.auto_approve_max_risk),
        auto_reject_min_risk: Number(rules.auto_reject_min_risk),
        quality_gate_paid_min_quality: Number(rules.quality_gate_paid_min_quality),
        revalidate_after_days: Number(rules.revalidate_after_days),
        max_batch_size: Number(rules.max_batch_size),
      });
      toast.success("Rules updated");
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Rules update failed");
    } finally {
      setRulesSaving(false);
    }
  };

  const resolveAppeal = async (appealId, status) => {
    try {
      await api.patch(`/moderation/features/appeals/${appealId}/resolve`, {
        status,
        moderator_note: status === "accepted" ? "Appeal accepted and re-opened for review." : "Appeal rejected after moderation review.",
      });
      toast.success(`Appeal ${status}`);
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Appeal resolution failed");
    }
  };

  const runRevalidation = async () => {
    try {
      setActionLoading(true);
      const res = await api.post("/moderation/features/revalidate/run", {
        run_now: true,
        limit: 25,
      });
      toast.success(`Revalidated ${res.data.scheduled_targets || 0} notes`);
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Revalidation failed");
    } finally {
      setActionLoading(false);
    }
  };

  const batchRunAI = async () => {
    try {
      setActionLoading(true);
      const ids = data.map((n) => n.id);
      const res = await api.post("/moderation/features/batch/run-ai", {
        note_ids: ids,
        force: false,
      });
      toast.success(`Batch AI processed ${res.data.processed} notes`);
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Batch AI failed");
    } finally {
      setActionLoading(false);
    }
  };

  const autoApproveSafeBatch = async () => {
    try {
      setActionLoading(true);
      const safeIds = (queueInfo.top || [])
        .filter((q) => q.priority <= 20)
        .map((q) => q.note_id);
      if (!safeIds.length) {
        toast("No safe notes in current conflict queue");
        return;
      }
      const res = await api.post("/moderation/features/batch/decision", {
        note_ids: safeIds,
        action: "approve",
        reason: "Auto-approved by safe batch rule",
      });
      toast.success(`Approved ${res.data.changed_count} safe notes`);
      await fetchAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Batch approve failed");
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const data =
    tab === "pending" ? pending : tab === "rejected" ? rejected : approved;

  const total = pending.length + rejected.length + approved.length;
  const tabStyles = {
    pending: {
      active: "border-amber-300 bg-amber-100 text-amber-900",
      idle: "border-neutral-200 bg-white text-neutral-500 hover:border-amber-200 hover:text-amber-700",
      badge: "bg-amber-500",
      label: "Pending",
      icon: "⏳",
    },
    rejected: {
      active: "border-rose-300 bg-rose-100 text-rose-900",
      idle: "border-neutral-200 bg-white text-neutral-500 hover:border-rose-200 hover:text-rose-700",
      badge: "bg-rose-500",
      label: "Rejected",
      icon: "✕",
    },
    approved: {
      active: "border-emerald-300 bg-emerald-100 text-emerald-900",
      idle: "border-neutral-200 bg-white text-neutral-500 hover:border-emerald-200 hover:text-emerald-700",
      badge: "bg-emerald-500",
      label: "Approved",
      icon: "✓",
    },
  };

  return (
    <Layout title="Moderation Dashboard">
      <section className="mesh-panel elevate-card rise-in overflow-hidden rounded-3xl border border-neutral-200 p-6 sm:p-8">
        <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.24em] text-neutral-500">Trust & Review</p>
            <h2 className="text-3xl font-black tracking-tight text-neutral-900 sm:text-4xl">Moderator Workbench</h2>
            <p className="mt-2 text-sm font-medium text-neutral-500">Review note quality, run AI checks, and publish decisions quickly.</p>
          </div>

          <button
            onClick={fetchAll}
            className="rounded-2xl border border-neutral-300 bg-white px-5 py-2.5 text-sm font-bold uppercase tracking-wide text-neutral-700 transition-all hover:-translate-y-0.5 hover:border-cyan-300 hover:text-cyan-700"
          >
            Refresh Data
          </button>
        </div>

        <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-amber-700">Pending</p>
            <p className="mt-2 text-3xl font-black text-amber-900">{pending.length}</p>
          </div>
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-rose-700">Rejected</p>
            <p className="mt-2 text-3xl font-black text-rose-900">{rejected.length}</p>
          </div>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-700">Approved</p>
            <p className="mt-2 text-3xl font-black text-emerald-900">{approved.length}</p>
          </div>
        </div>

        {analytics && (
          <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-4">
            <div className="rounded-2xl border border-neutral-200 bg-white p-4">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Open Appeals</p>
              <p className="mt-2 text-2xl font-black text-neutral-900">{analytics.queue?.open_appeals ?? 0}</p>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-white p-4">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">AI Valid Rate</p>
              <p className="mt-2 text-2xl font-black text-neutral-900">{Math.round((analytics.ai?.valid_rate || 0) * 100)}%</p>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-white p-4">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Conflict Queue</p>
              <p className="mt-2 text-2xl font-black text-neutral-900">{queueInfo.count}</p>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-white p-4">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">30d Decisions</p>
              <p className="mt-2 text-2xl font-black text-neutral-900">
                {(analytics.decisions?.approved || 0) + (analytics.decisions?.rejected || 0)}
              </p>
            </div>
          </div>
        )}

        {confidenceTrend.length > 0 && (
          <div className="mb-6 rounded-2xl border border-neutral-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">AI Confidence Trend (14d)</p>
              <p className="text-xs font-semibold text-neutral-400">{confidenceTrend.length} points</p>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
              {confidenceTrend.slice(-7).map((point) => (
                <div key={point.day} className="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                  <p className="text-xs font-bold text-neutral-600">{point.day.slice(5)}</p>
                  <p className="mt-1 text-sm font-black text-neutral-900">{Math.round((point.valid_rate || 0) * 100)}%</p>
                  <p className="text-[11px] font-medium text-neutral-500">Risk {Math.round(point.avg_risk || 0)}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {rules && (
          <div className="mb-6 rounded-2xl border border-neutral-200 bg-white p-4">
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Moderation Rules</p>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              <label className="text-xs font-semibold text-neutral-500">
                Auto Approve Max Risk
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={rules.auto_approve_max_risk ?? 20}
                  onChange={(e) => setRules((prev) => ({ ...prev, auto_approve_max_risk: Number(e.target.value) }))}
                  className="mt-1 w-full rounded-lg border border-neutral-300 px-2 py-1.5 text-sm font-semibold text-neutral-800"
                />
              </label>
              <label className="text-xs font-semibold text-neutral-500">
                Auto Reject Min Risk
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={rules.auto_reject_min_risk ?? 70}
                  onChange={(e) => setRules((prev) => ({ ...prev, auto_reject_min_risk: Number(e.target.value) }))}
                  className="mt-1 w-full rounded-lg border border-neutral-300 px-2 py-1.5 text-sm font-semibold text-neutral-800"
                />
              </label>
              <label className="text-xs font-semibold text-neutral-500">
                Paid Quality Min
                <input
                  type="number"
                  min={0}
                  max={1}
                  step={0.01}
                  value={rules.quality_gate_paid_min_quality ?? 0.55}
                  onChange={(e) => setRules((prev) => ({ ...prev, quality_gate_paid_min_quality: Number(e.target.value) }))}
                  className="mt-1 w-full rounded-lg border border-neutral-300 px-2 py-1.5 text-sm font-semibold text-neutral-800"
                />
              </label>
              <label className="text-xs font-semibold text-neutral-500">
                Revalidate Days
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={rules.revalidate_after_days ?? 14}
                  onChange={(e) => setRules((prev) => ({ ...prev, revalidate_after_days: Number(e.target.value) }))}
                  className="mt-1 w-full rounded-lg border border-neutral-300 px-2 py-1.5 text-sm font-semibold text-neutral-800"
                />
              </label>
              <label className="text-xs font-semibold text-neutral-500">
                Max Batch
                <input
                  type="number"
                  min={1}
                  max={200}
                  value={rules.max_batch_size ?? 50}
                  onChange={(e) => setRules((prev) => ({ ...prev, max_batch_size: Number(e.target.value) }))}
                  className="mt-1 w-full rounded-lg border border-neutral-300 px-2 py-1.5 text-sm font-semibold text-neutral-800"
                />
              </label>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                disabled={rulesSaving}
                onClick={saveRules}
                className="rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2 text-xs font-bold uppercase tracking-wide text-white hover:bg-neutral-700 disabled:opacity-60"
              >
                {rulesSaving ? "Saving..." : "Save Rules"}
              </button>
              <button
                disabled={actionLoading}
                onClick={runRevalidation}
                className="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-xs font-bold uppercase tracking-wide text-neutral-700 hover:border-cyan-300 hover:text-cyan-700 disabled:opacity-60"
              >
                Run Revalidation
              </button>
            </div>
          </div>
        )}

        {appeals.length > 0 && (
          <div className="mb-6 rounded-2xl border border-neutral-200 bg-white p-4">
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Open Appeals</p>
            <div className="space-y-2">
              {appeals.slice(0, 5).map((appeal) => (
                <div key={appeal.id} className="flex flex-col gap-2 rounded-xl border border-neutral-200 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-bold text-neutral-900">{appeal.note_title || "Untitled Note"}</p>
                    <p className="text-xs font-medium text-neutral-500">{appeal.message}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => resolveAppeal(appeal.id, "accepted")}
                      className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-emerald-800"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => resolveAppeal(appeal.id, "rejected")}
                      className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-1.5 text-xs font-bold uppercase tracking-wide text-rose-800"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mb-6 flex flex-wrap gap-2">
          <button
            disabled={actionLoading}
            onClick={batchRunAI}
            className="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-bold uppercase tracking-wide text-neutral-700 hover:border-cyan-300 hover:text-cyan-700 disabled:opacity-60"
          >
            Run AI For Current Tab
          </button>
          <button
            disabled={actionLoading}
            onClick={autoApproveSafeBatch}
            className="rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-bold uppercase tracking-wide text-white hover:bg-neutral-700 disabled:opacity-60"
          >
            Auto-Approve Safe Batch
          </button>
        </div>

        <div className="mb-6 flex flex-wrap gap-2">
          {["pending", "rejected", "approved"].map((key) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-bold uppercase tracking-wide transition-colors ${
                tab === key ? tabStyles[key].active : tabStyles[key].idle
              }`}
            >
              <span className={`inline-flex h-2.5 w-2.5 rounded-full ${tabStyles[key].badge}`} />
              {tabStyles[key].label} ({key === "pending" ? pending.length : key === "rejected" ? rejected.length : approved.length})
            </button>
          ))}
        </div>

        <div className="mb-4 flex items-center justify-between border-b border-neutral-200 pb-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-neutral-500">Showing {tabStyles[tab].label}</p>
          <p className="text-xs font-semibold text-neutral-400">{total} notes in moderation pipeline</p>
        </div>

        {loading ? (
          <div className="rounded-2xl border border-neutral-200 bg-white p-12">
            <Spinner label="Loading moderation data..." />
          </div>
        ) : data.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 bg-white p-12 text-center">
            <div className="mb-3 text-5xl">{tabStyles[tab].icon}</div>
            <h3 className="text-xl font-black uppercase tracking-tight text-neutral-800">No {tabStyles[tab].label} Notes</h3>
            <p className="mt-2 text-sm font-medium text-neutral-500">You are all caught up for this queue.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {data.map((n) => (
              <article key={n.id} className="rise-in elevate-card rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="flex-1">
                    <h3 className="text-xl font-black tracking-tight text-neutral-900">{n.title}</h3>
                    <p className="mt-1 text-sm font-semibold text-neutral-500">{n.dept} • Semester {n.semester} • {n.subject} • Unit {n.unit}</p>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {tab === "rejected" && (
                        <span className="rounded-full border border-rose-200 bg-rose-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-rose-700">
                          {n.rejected_reason || "Rejected"}
                        </span>
                      )}
                      {tab === "approved" && n.approved_at && (
                        <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-emerald-700">
                          Approved {new Date(n.approved_at * 1000).toLocaleDateString()}
                        </span>
                      )}
                      {n.ai ? (
                        <span className="rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-cyan-700">
                          AI Quality {Math.round((n.ai.quality_score || 0) * 100)}%
                        </span>
                      ) : (
                        <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold uppercase tracking-wide text-amber-700">
                          AI Pending
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {tab !== "approved" && (
                      <button
                        onClick={() => runAI(n.id)}
                        className="rounded-xl border border-cyan-300 bg-cyan-50 px-4 py-2 text-sm font-bold uppercase tracking-wide text-cyan-800 transition-colors hover:bg-cyan-100"
                      >
                        Run AI
                      </button>
                    )}
                    <button
                      onClick={() => openNote(n)}
                      className="rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-bold uppercase tracking-wide text-white transition-colors hover:bg-neutral-700"
                    >
                      Review
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {/* Review Modal */}
      {open && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  <span>🧠</span> Review Note (AI Assisted)
                </h3>
                <button
                  onClick={() => {
                    setOpen(false);
                    setSelected(null);
                    setRejectReason("");
                    setPreviewUrl("");
                    if (previewUrl) {
                      URL.revokeObjectURL(previewUrl);
                    }
                  }}
                  className="text-slate-400 hover:text-slate-200 transition-colors"
                >
                  ✕
                </button>
              </div>

              {!selected ? (
                <p className="text-slate-400">No note selected.</p>
              ) : (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-semibold text-slate-100">{selected.title}</h3>
                    <p className="text-slate-400 text-sm mt-1">
                      {selected.dept} • Sem {selected.semester} • {selected.subject} • Unit{" "}
                      {selected.unit}
                    </p>
                    {selected.is_paid && (
                      <p className="text-yellow-400 text-sm mt-1">💰 Paid: ₹{selected.price}</p>
                    )}

                    {tab === "rejected" && (
                      <div className="mt-3 p-3 bg-gradient-to-br from-red-500/20 to-rose-500/20 border border-red-500/30 rounded-xl">
                        <p className="text-red-200 font-semibold flex items-center gap-2">
                          <span>❌</span> Rejection Reason
                        </p>
                        <p className="text-red-300 text-sm mt-1">{selected.rejected_reason || "Rejected"}</p>
                      </div>
                    )}
                  </div>

                  {/* AI Report */}
                  <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="font-semibold text-slate-100 flex items-center gap-2">
                        <span>🧠</span> AI Report
                      </h4>

                      {!selected.ai && tab !== "approved" && (
                        <button
                          onClick={() => runAI(selected.id)}
                          className="px-3 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 text-white hover:from-indigo-600 hover:to-indigo-700 transition-all duration-200 text-sm font-medium"
                        >
                          Run AI Now
                        </button>
                      )}
                    </div>

                    {!selected.ai ? (
                      <p className="text-slate-400 mt-3">AI analysis not available.</p>
                    ) : (
                      <div className="mt-3 space-y-4">
                        {/* Analysis Header with Timestamp */}
                        <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-slate-300">AI Analysis Record</p>
                              <p className="text-xs text-slate-400">
                                Analyzed on: {new Date().toLocaleString()}
                              </p>
                            </div>
                            <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                              selected.ai.validation_success 
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' 
                                : 'bg-red-500/20 text-red-300 border border-red-500/30'
                            }`}>
                              {selected.ai.validation_success ? 'VALID' : 'INVALID'}
                            </div>
                          </div>
                        </div>

                        {/* Validation Status */}
                        <div className={`rounded-xl p-4 border ${
                          selected.ai.validation_success 
                            ? 'bg-gradient-to-br from-emerald-500/20 to-green-500/20 border-emerald-500/30' 
                            : 'bg-gradient-to-br from-red-500/20 to-rose-500/20 border-red-500/30'
                        }`}>
                          <p className="font-semibold text-slate-100 mb-2">
                            {selected.ai.validation_success ? '✅ Content Valid' : '❌ Content Invalid'}
                          </p>
                          <p className="text-sm text-slate-300">
                            {selected.ai.validation_message}
                          </p>
                        </div>

                        {/* Critical Issues */}
                        {selected.ai.critical_issues?.length > 0 && (
                          <div className="bg-gradient-to-br from-red-500/20 to-rose-500/20 border border-red-500/30 rounded-xl p-3">
                            <p className="text-red-200 font-semibold flex items-center gap-2 mb-2">
                              <span>🚨</span> Critical Issues ({selected.ai.critical_issues.length})
                            </p>
                            <ul className="text-red-300 text-sm space-y-1">
                              {selected.ai.critical_issues.map((issue, i) => (
                                <li key={i} className="flex items-start gap-2">
                                  <span className="text-red-400 mt-1">•</span>
                                  <span>{issue}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Metadata Comparison */}
                        {selected.ai.metadata && (
                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-sm font-medium text-slate-300 mb-2">📋 Metadata Analyzed:</p>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div>
                                <span className="text-slate-400">Title:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.title}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Description:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.description || 'No description'}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Subject:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.subject}</p>
                              </div>
                              <div>
                                <span className="text-slate-400">Tags:</span>
                                <p className="text-slate-200 truncate">{selected.ai.metadata.tags?.join(', ') || 'No tags'}</p>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* AI Analysis Summary */}
                        <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/20 rounded-xl p-3">
                          <p className="text-sm font-medium text-slate-300 mb-2">🤖 AI Analysis Summary:</p>
                          <p className="text-sm text-slate-400">{selected.ai.report?.summary}</p>
                        </div>

                        {/* Content Topics */}
                        {selected.ai.report?.topics?.length > 0 && (
                          <div>
                            <p className="text-sm font-medium text-slate-300 mb-2">🏷️ Topics Found:</p>
                            <div className="flex flex-wrap gap-2">
                              {selected.ai.report.topics.map((t, i) => (
                                <span
                                  key={i}
                                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-r from-indigo-500/20 to-purple-500/20 text-indigo-300 border border-indigo-500/30"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Validation Scores Grid */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">🎯 Spam Score</p>
                            <p className="text-lg font-bold text-slate-200">
                              {selected.ai.report?.spam_score || 0}%
                            </p>
                            <p className="text-xs text-slate-500">
                              {selected.ai.report?.spam_score < 30 ? 'Low Risk' : selected.ai.report?.spam_score < 70 ? 'Medium Risk' : 'High Risk'}
                            </p>
                          </div>

                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">✅ Content Valid</p>
                            <p className="text-lg font-bold text-slate-200">
                              {selected.ai.report?.content_valid ? '✅ Valid' : '❌ Invalid'}
                            </p>
                            <p className="text-xs text-slate-500">
                              {selected.ai.report?.content_valid ? 'Matches metadata' : 'Does not match'}
                            </p>
                          </div>

                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">📚 Subject Match</p>
                            <p className="text-lg font-bold text-slate-200">
                              {selected.ai.report?.subject_match ? '✅ Match' : '❌ Mismatch'}
                            </p>
                            <p className="text-xs text-slate-500">
                              {selected.ai.report?.subject_match ? 'Correct subject' : 'Wrong subject'}
                            </p>
                          </div>

                          <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-3">
                            <p className="text-xs text-slate-400">🏷️ Tags Relevant</p>
                            <p className="text-lg font-bold text-slate-200">
                              {selected.ai.report?.tags_relevance ? '✅ Relevant' : '❌ Irrelevant'}
                            </p>
                            <p className="text-xs text-slate-500">
                              {selected.ai.report?.tags_relevance ? 'Tags match content' : 'Tags do not match'}
                            </p>
                          </div>
                        </div>

                        {/* Warnings */}
                        {selected.ai.report?.warnings?.length > 0 && (
                          <div className="bg-gradient-to-br from-yellow-500/20 to-amber-500/20 border border-yellow-500/30 rounded-xl p-3">
                            <p className="text-yellow-200 font-semibold flex items-center gap-2 mb-2">
                              <span>⚠️</span> Warnings ({selected.ai.report.warnings.length})
                            </p>
                            <ul className="text-yellow-300 text-sm space-y-1">
                              {selected.ai.report.warnings.map((warning, i) => (
                                <li key={i} className="flex items-start gap-2">
                                  <span className="text-yellow-400 mt-1">•</span>
                                  <span>{warning}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* PII Detection */}
                        {selected.ai.personal_info?.emails?.length > 0 || selected.ai.personal_info?.phones?.length > 0 ? (
                          <div className="bg-gradient-to-br from-red-500/20 to-rose-500/20 border border-red-500/30 rounded-xl p-3">
                            <p className="text-red-200 font-semibold flex items-center gap-2">
                              <span>🚨</span> Personal Information Found
                            </p>
                            <div className="text-red-300 text-sm mt-2 space-y-1">
                              {selected.ai.personal_info.emails?.length > 0 && (
                                <div>
                                  <span className="font-medium">Emails:</span> {selected.ai.personal_info.emails.join(', ')}
                                </div>
                              )}
                              {selected.ai.personal_info.phones?.length > 0 && (
                                <div>
                                  <span className="font-medium">Phones:</span> {selected.ai.personal_info.phones.join(', ')}
                                </div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="bg-gradient-to-br from-emerald-500/20 to-green-500/20 border border-emerald-500/30 rounded-xl p-3">
                            <p className="text-emerald-200 font-semibold flex items-center gap-2">
                              <span>✅</span> No Personal Information Detected
                            </p>
                            <p className="text-emerald-300 text-sm mt-1">Content appears to be clean of personal data</p>
                          </div>
                        )}

                        {/* Re-run AI Button */}
                        <div className="flex justify-center pt-4">
                          <button
                            onClick={() => runAI(selected.id)}
                            className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 text-white hover:from-indigo-600 hover:to-purple-700 transition-all duration-200 text-sm font-medium"
                          >
                            🔄 Re-run Analysis
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="bg-gradient-to-br from-cyan-500/10 to-indigo-500/10 border border-cyan-500/20 rounded-xl p-4">
                    <h4 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                      <span>🧭</span> Moderation Signals
                    </h4>

                    {insightsLoading ? (
                      <Spinner label="Loading signals..." />
                    ) : (
                      <div className="space-y-3">
                        {insights.explain && (
                          <div className="rounded-xl border border-slate-600/50 bg-slate-800/40 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Why Flagged</p>
                            <p className="mt-1 text-sm text-slate-200">{insights.explain.explanation}</p>
                          </div>
                        )}

                        {insights.quality && (
                          <div className={`rounded-xl border p-3 ${insights.quality.passed ? "border-emerald-500/30 bg-emerald-500/10" : "border-amber-500/30 bg-amber-500/10"}`}>
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-300">Paid Quality Gate</p>
                            <p className="mt-1 text-sm text-slate-100">
                              {insights.quality.reason}
                              {typeof insights.quality.quality_score === "number" && (
                                <> ({Math.round(insights.quality.quality_score * 100)}% / min {Math.round((insights.quality.minimum_required || 0) * 100)}%)</>
                              )}
                            </p>
                          </div>
                        )}

                        {!!insights.suggestedTags.length && (
                          <div className="rounded-xl border border-slate-600/50 bg-slate-800/40 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Suggested Tags</p>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {insights.suggestedTags.map((tag) => (
                                <span key={tag} className="rounded-full border border-cyan-400/40 bg-cyan-500/10 px-2 py-1 text-xs font-semibold text-cyan-200">
                                  #{tag}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {!!insights.duplicates.length && (
                          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-rose-200">Potential Duplicates</p>
                            <div className="mt-1 space-y-1">
                              {insights.duplicates.slice(0, 3).map((dup) => (
                                <p key={dup.note_id} className="text-xs text-rose-100">
                                  {dup.title || "Untitled"} ({Math.round((dup.similarity || 0) * 100)}%)
                                </p>
                              ))}
                            </div>
                          </div>
                        )}

                        {insights.trust && (
                          <div className="rounded-xl border border-slate-600/50 bg-slate-800/40 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Creator Trust</p>
                            <p className="mt-1 text-sm text-slate-200">
                              Level {insights.trust.level || "new"} • Avg AI Risk {Math.round(insights.trust.avg_ai_risk || 0)} • Analyzed {insights.trust.analyzed_notes || 0}
                            </p>
                          </div>
                        )}

                        {insights.diff && (
                          <div className="rounded-xl border border-slate-600/50 bg-slate-800/40 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Metadata vs Content Match</p>
                            <p className="mt-1 text-sm text-slate-200">
                              Matched tokens: {(insights.diff.matched_tokens || []).slice(0, 10).join(", ") || "None"}
                            </p>
                          </div>
                        )}

                        {!!insights.timeline.length && (
                          <div className="rounded-xl border border-slate-600/50 bg-slate-800/40 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Audit Timeline</p>
                            <div className="mt-2 max-h-36 space-y-1 overflow-auto">
                              {insights.timeline.slice(0, 10).map((event, index) => (
                                <p key={`${event.type}-${event.ts}-${index}`} className="text-xs text-slate-300">
                                  {new Date((event.ts || 0) * 1000).toLocaleString()} • {event.type}
                                </p>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Preview */}
                  <div className="bg-gradient-to-br from-slate-800/50 to-slate-700/30 border border-slate-600/50 rounded-xl p-4">
                    <h4 className="font-semibold text-slate-100 mb-3 flex items-center gap-2">
                      <span>📄</span> Secure Preview
                    </h4>

                    {previewLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Spinner label="Loading preview..." />
                      </div>
                    ) : previewUrl ? (
                      <div className="rounded-xl overflow-hidden border border-slate-600/50">
                        <iframe
                          src={previewUrl}
                          title="Secure Preview"
                          className="w-full"
                          style={{ height: "450px" }}
                        />
                      </div>
                    ) : (
                      <p className="text-slate-400">No preview loaded.</p>
                    )}
                  </div>

                  {/* Actions */}
                  {tab === "pending" && (
                    <>
                      <div className="flex gap-3">
                        <button
                          onClick={() => approveNote(selected.id)}
                          disabled={actionLoading}
                          className={`px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
                            actionLoading
                              ? "bg-emerald-600/30 text-emerald-300 cursor-not-allowed"
                              : "bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/25"
                          }`}
                        >
                          {actionLoading ? "..." : "✅ Approve"}
                        </button>

                        <button
                          onClick={() => rejectNote(selected.id)}
                          disabled={actionLoading}
                          className={`px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
                            actionLoading
                              ? "bg-red-600/30 text-red-300 cursor-not-allowed"
                              : "bg-gradient-to-r from-red-500 to-rose-600 text-white hover:from-red-600 hover:to-rose-700 shadow-lg shadow-red-500/25"
                          }`}
                        >
                          {actionLoading ? "..." : "❌ Reject"}
                        </button>
                      </div>

                      <textarea
                        className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-600/50 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all duration-200"
                        placeholder="Reject reason (required if rejecting)"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        rows={3}
                      />
                    </>
                  )}

                  {tab === "rejected" && (
                    <button
                      onClick={() => overrideApprove(selected.id)}
                      disabled={actionLoading}
                      className={`w-full px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
                        actionLoading
                          ? "bg-emerald-600/30 text-emerald-300 cursor-not-allowed"
                          : "bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:from-emerald-600 hover:to-teal-700 shadow-lg shadow-emerald-500/25"
                      }`}
                    >
                      {actionLoading ? "..." : "✅ Override Approve"}
                    </button>
                  )}

                  {tab === "approved" && (
                    <>
                      <button
                        onClick={() => overrideReject(selected.id)}
                        disabled={actionLoading}
                        className={`w-full px-6 py-3 rounded-xl font-semibold transition-all duration-200 ${
                          actionLoading
                            ? "bg-red-600/30 text-red-300 cursor-not-allowed"
                            : "bg-gradient-to-r from-red-500 to-rose-600 text-white hover:from-red-600 hover:to-rose-700 shadow-lg shadow-red-500/25"
                        }`}
                      >
                        {actionLoading ? "..." : "❌ Override Reject (Take Down)"}
                      </button>

                      <textarea
                        className="w-full px-4 py-3 rounded-xl bg-slate-800/50 border border-slate-600/50 text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent transition-all duration-200"
                        placeholder="Take down reason (required)"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        rows={3}
                      >
                      </textarea>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
