function toNumber(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function toStringOr(v, fallback = "") {
  return typeof v === "string" ? v : fallback;
}

export function normalizePurchaseRecord(raw = {}) {
  const note = raw.note || {};
  const amount = toNumber(raw.amount, 0);
  const isPaid = Boolean(note.is_paid ?? amount > 0);
  return {
    id: toStringOr(raw.id, ""),
    purchase_id: toStringOr(raw.purchase_id || raw.id, ""),
    note_id: toStringOr(raw.note_id, ""),
    amount,
    status: toStringOr(raw.status, ""),
    created_at: toNumber(raw.created_at, 0),
    unlocked_type: toStringOr(raw.unlocked_type, isPaid ? "paid" : "free"),
    unlocked_at: toNumber(raw.unlocked_at ?? raw.created_at, 0),
    note: {
      id: toStringOr(note.id || raw.note_id, ""),
      title: toStringOr(note.title, "Note unavailable"),
      subject: toStringOr(note.subject, "Unknown subject"),
      unit: note.unit ?? null,
      semester: note.semester ?? null,
      dept: toStringOr(note.dept, ""),
      description: toStringOr(note.description, ""),
      is_paid: isPaid,
      price: toNumber(note.price, amount),
    },
  };
}

export function normalizeLibraryRecord(raw = {}) {
  const isPaid = Boolean(raw.is_paid ?? toNumber(raw.price, 0) > 0);
  return {
    purchase_id: toStringOr(raw.purchase_id || raw.id, ""),
    note_id: toStringOr(raw.note_id, ""),
    title: toStringOr(raw.title, "Untitled"),
    subject: toStringOr(raw.subject, ""),
    unit: raw.unit ?? null,
    semester: raw.semester ?? null,
    dept: toStringOr(raw.dept, ""),
    description: toStringOr(raw.description, ""),
    is_paid: isPaid,
    price: toNumber(raw.price, 0),
    unlocked_type: toStringOr(raw.unlocked_type, isPaid ? "paid" : "free"),
    unlocked_at: toNumber(raw.unlocked_at ?? raw.created_at, 0),
  };
}
