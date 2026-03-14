import { useCallback, useEffect, useMemo, useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";
import toast from "react-hot-toast";

function formatReason(reason) {
  const raw = String(reason || "").trim();
  if (!raw) return "Wallet Update";

  const directMap = {
    signup_bonus: "Signup Bonus",
    "signup_bonus_backfill:v1": "Initial Points Backfill",
    note_publish_initiated: "Note Publish Reward",
    note_purchase_points_debit: "Note Purchase (Points)",
    note_sale_points_credit: "Note Sale Credit",
    creator_pass_purchase_points_debit: "Creator Pass Purchase",
    creator_pass_sale_points_credit: "Creator Pass Sale Credit",
    dispute_refund_points_credit: "Dispute Refund Credit",
    dispute_refund_points_debit: "Dispute Refund Debit",
  };
  if (directMap[raw]) return directMap[raw];

  if (raw.startsWith("top_contributor_bonus:")) return "Top Contributor Bonus";

  return raw
    .replace(/[:_]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function Wallet() {
  const [loading, setLoading] = useState(true);
  const [balance, setBalance] = useState(0);
  const [transactions, setTransactions] = useState([]);
  const [limit, setLimit] = useState(50);

  const loadWallet = useCallback(async (txLimit = limit) => {
    try {
      setLoading(true);
      const [meRes, txRes] = await Promise.all([
        api.get(ENDPOINTS.wallet.me),
        api.get(`${ENDPOINTS.wallet.transactions}?limit=${txLimit}`),
      ]);
      setBalance(Number(meRes.data?.wallet_points || 0));
      setTransactions(txRes.data?.transactions || []);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load wallet");
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    loadWallet();
  }, [loadWallet]);

  const summary = useMemo(() => {
    let earned = 0;
    let spent = 0;
    for (const tx of transactions) {
      const points = Number(tx?.points || 0);
      if (points >= 0) earned += points;
      else spent += Math.abs(points);
    }
    return { earned, spent };
  }, [transactions]);

  return (
    <Layout title="Wallet">
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Metric title="Current Balance" value={`${balance} pts`} />
          <Metric title="Total Earned" value={`${summary.earned} pts`} />
          <Metric title="Total Spent" value={`${summary.spent} pts`} />
        </div>

        <div className="border border-black bg-white p-6">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <h3 className="text-sm font-black uppercase tracking-wider text-black">Wallet Transactions</h3>
            <select
              className="input-surface max-w-xs"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value, 10) || 50)}
            >
              <option value={25}>Last 25</option>
              <option value={50}>Last 50</option>
              <option value={100}>Last 100</option>
              <option value={200}>Last 200</option>
            </select>
            <button onClick={() => loadWallet(limit)} className="btn-primary px-4 py-2 text-xs">
              Refresh
            </button>
            <a
              href={`${api.defaults.baseURL || ""}${ENDPOINTS.wallet.transactionsExport}`}
              download="wallet_transactions.csv"
              className="btn-secondary px-4 py-2 text-xs"
            >
              Export CSV
            </a>
          </div>

          {loading ? (
            <p className="text-sm text-zinc-500">Loading wallet...</p>
          ) : transactions.length === 0 ? (
            <p className="text-sm text-zinc-500">No wallet transactions yet.</p>
          ) : (
            <div className="space-y-2">
              {transactions.map((tx) => {
                const points = Number(tx.points || 0);
                const positive = points >= 0;
                return (
                  <div key={tx.id} className="flex items-center justify-between border border-zinc-200 px-3 py-3 text-xs">
                    <div>
                      <p className="font-black uppercase text-zinc-800">{formatReason(tx.reason)}</p>
                      {tx.reason && formatReason(tx.reason) !== tx.reason && (
                        <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">{tx.reason}</p>
                      )}
                      <p className="font-bold text-zinc-500">{new Date((tx.created_at || 0) * 1000).toLocaleString()}</p>
                    </div>
                    <p className={`font-black uppercase ${positive ? "text-green-700" : "text-red-700"}`}>
                      {positive ? "+" : "-"}{Math.abs(points)} pts
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

function Metric({ title, value }) {
  return (
    <div className="border border-black bg-white p-4">
      <p className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-500">{title}</p>
      <p className="mt-2 text-2xl font-black uppercase tracking-tight text-black">{value}</p>
    </div>
  );
}
