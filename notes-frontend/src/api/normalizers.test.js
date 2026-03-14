import test from "node:test";
import assert from "node:assert/strict";

import { normalizeLibraryRecord, normalizePurchaseRecord } from "./normalizers.js";

test("normalizePurchaseRecord builds safe defaults", () => {
  const row = normalizePurchaseRecord({
    id: "p1",
    note_id: "n1",
    amount: "49",
    note: { title: "OS Unit 1", is_paid: true, price: 49 },
  });
  assert.equal(row.id, "p1");
  assert.equal(row.note_id, "n1");
  assert.equal(row.amount, 49);
  assert.equal(row.note.title, "OS Unit 1");
  assert.equal(row.note.is_paid, true);
});

test("normalizeLibraryRecord keeps free items consistent", () => {
  const row = normalizeLibraryRecord({
    purchase_id: "lib1",
    note_id: "n2",
    title: "Math Quick Revision",
    is_paid: false,
    price: 0,
  });
  assert.equal(row.purchase_id, "lib1");
  assert.equal(row.is_paid, false);
  assert.equal(row.unlocked_type, "free");
});
