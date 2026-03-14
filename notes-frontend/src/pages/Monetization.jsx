import { useCallback, useEffect, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import toast from "react-hot-toast";

const INITIAL_COUPON = { code: "", percent_off: 10, max_uses: 100, note_id: "" };
const INITIAL_CAMPAIGN = { note_id: "", title: "", discount_percent: 15, starts_at: "", ends_at: "" };

export default function Monetization() {
  const [coupons, setCoupons] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [payouts, setPayouts] = useState({ total_earned_inr: 0, total_earned_points: 0, entries: [] });
  const [myNotes, setMyNotes] = useState([]);
  const [couponForm, setCouponForm] = useState(INITIAL_COUPON);
  const [campaignForm, setCampaignForm] = useState(INITIAL_CAMPAIGN);

  const loadAll = useCallback(async () => {
    try {
      const [c, ca, p, notesRes] = await Promise.all([
        api.get(ENDPOINTS.monetization.couponsMine),
        api.get(ENDPOINTS.monetization.campaignsMine),
        api.get(ENDPOINTS.monetization.payoutsMine),
        api.get(ENDPOINTS.notes.mine),
      ]);
      setCoupons(c.data || []);
      setCampaigns(ca.data || []);
      setPayouts(p.data || { total_earned_inr: 0, total_earned_points: 0, entries: [] });
      setMyNotes((notesRes.data || []).filter((n) => n?.id));
    } catch {
      toast.error("Failed to load monetization data");
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      loadAll();
    }, 0);
    return () => clearTimeout(t);
  }, [loadAll]);

  const createCoupon = async () => {
    try {
      await api.post(ENDPOINTS.monetization.couponsCreate, {
        ...couponForm,
        code: couponForm.code.trim().toUpperCase(),
        note_id: couponForm.note_id.trim() || undefined,
      });
      toast.success("Coupon created");
      setCouponForm(INITIAL_COUPON);
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create coupon");
    }
  };

  const createCampaign = async () => {
    try {
      const startsAt = Math.floor(new Date(campaignForm.starts_at).getTime() / 1000);
      const endsAt = Math.floor(new Date(campaignForm.ends_at).getTime() / 1000);
      await api.post(ENDPOINTS.monetization.campaignsCreate, {
        ...campaignForm,
        starts_at: startsAt,
        ends_at: endsAt,
      });
      toast.success("Campaign created");
      setCampaignForm(INITIAL_CAMPAIGN);
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create campaign");
    }
  };

  return (
    <Layout title="Monetization">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="border border-black bg-white p-6">
          <h3 className="mb-4 text-sm font-black uppercase tracking-wider">Create Coupon</h3>
          <div className="space-y-3">
            <input className="input-surface" placeholder="Code (e.g. SAVE20)" value={couponForm.code} onChange={(e) => setCouponForm((p) => ({ ...p, code: e.target.value }))} />
            <input className="input-surface" type="number" min={1} max={90} value={couponForm.percent_off} onChange={(e) => setCouponForm((p) => ({ ...p, percent_off: parseInt(e.target.value, 10) || 1 }))} />
            <input className="input-surface" type="number" min={1} value={couponForm.max_uses} onChange={(e) => setCouponForm((p) => ({ ...p, max_uses: parseInt(e.target.value, 10) || 1 }))} />
            <select className="input-surface" value={couponForm.note_id} onChange={(e) => setCouponForm((p) => ({ ...p, note_id: e.target.value }))}>
              <option value="">All my notes</option>
              {myNotes.map((n) => (
                <option key={n.id} value={n.id}>{n.title}</option>
              ))}
            </select>
            <button onClick={createCoupon} className="btn-primary w-full">Create Coupon</button>
          </div>
        </div>

        <div className="border border-black bg-white p-6">
          <h3 className="mb-4 text-sm font-black uppercase tracking-wider">Create Campaign</h3>
          <div className="space-y-3">
            <select className="input-surface" value={campaignForm.note_id} onChange={(e) => setCampaignForm((p) => ({ ...p, note_id: e.target.value }))}>
              <option value="">Select note</option>
              {myNotes.map((n) => (
                <option key={n.id} value={n.id}>{n.title}</option>
              ))}
            </select>
            <input className="input-surface" placeholder="Title" value={campaignForm.title} onChange={(e) => setCampaignForm((p) => ({ ...p, title: e.target.value }))} />
            <input className="input-surface" type="number" min={1} max={90} value={campaignForm.discount_percent} onChange={(e) => setCampaignForm((p) => ({ ...p, discount_percent: parseInt(e.target.value, 10) || 1 }))} />
            <input className="input-surface" type="datetime-local" value={campaignForm.starts_at} onChange={(e) => setCampaignForm((p) => ({ ...p, starts_at: e.target.value }))} />
            <input className="input-surface" type="datetime-local" value={campaignForm.ends_at} onChange={(e) => setCampaignForm((p) => ({ ...p, ends_at: e.target.value }))} />
            <button onClick={createCampaign} className="btn-primary w-full">Create Campaign</button>
          </div>
        </div>

        <div className="border border-black bg-white p-6">
          <h3 className="mb-2 text-sm font-black uppercase tracking-wider">Payout History</h3>
          <p className="mb-1 text-2xl font-black uppercase tracking-tight text-black">INR {payouts.total_earned_inr || 0}</p>
          <p className="mb-4 text-sm font-bold uppercase tracking-wider text-zinc-500">Points {payouts.total_earned_points || 0}</p>
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {(payouts.entries || []).map((e) => (
              <div key={e.id} className="border border-zinc-200 p-2 text-xs">
                <p className="font-bold uppercase text-zinc-700">{e.entry_type}</p>
                <p className="font-black text-black">{e.currency || "INR"} {e.amount}</p>
                <p className="text-[10px] text-zinc-500">{new Date(e.created_at * 1000).toLocaleString()}</p>
              </div>
            ))}
            {(payouts.entries || []).length === 0 && <p className="text-xs text-zinc-500">No payouts yet.</p>}
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="border border-black bg-white p-6">
          <h3 className="mb-3 text-sm font-black uppercase tracking-wider">My Coupons</h3>
          <div className="space-y-2">
            {coupons.map((c) => (
              <div key={c.id} className="border border-zinc-200 p-3 text-xs">
                <p className="font-black uppercase">{c.code} - {c.percent_off}% OFF</p>
                <p className="text-zinc-600">Uses: {c.uses}/{c.max_uses}</p>
              </div>
            ))}
            {coupons.length === 0 && <p className="text-xs text-zinc-500">No coupons yet.</p>}
          </div>
        </div>
        <div className="border border-black bg-white p-6">
          <h3 className="mb-3 text-sm font-black uppercase tracking-wider">My Campaigns</h3>
          <div className="space-y-2">
            {campaigns.map((c) => (
              <div key={c.id} className="border border-zinc-200 p-3 text-xs">
                <p className="font-black uppercase">{c.title} - {c.discount_percent}%</p>
                <p className="text-zinc-600">Note: {c.note_id}</p>
              </div>
            ))}
            {campaigns.length === 0 && <p className="text-xs text-zinc-500">No campaigns yet.</p>}
          </div>
        </div>
      </div>
    </Layout>
  );
}
