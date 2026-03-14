import test from "node:test";
import assert from "node:assert/strict";

import { ENDPOINTS } from "./endpoints.js";

test("dynamic endpoint builders resolve expected paths", () => {
  assert.equal(ENDPOINTS.notes.details("123"), "/notes/123/details");
  assert.equal(ENDPOINTS.notes.smartStudyPack("123"), "/notes/123/smart-study-pack");
  assert.equal(ENDPOINTS.monetization.passSubscribe("p1"), "/monetization/passes/p1/subscribe");
});

test("seller analytics endpoints are available", () => {
  assert.equal(ENDPOINTS.seller.dashboard, "/seller/dashboard");
  assert.equal(ENDPOINTS.seller.funnel, "/seller/funnel");
  assert.equal(ENDPOINTS.seller.couponPerformance, "/seller/coupon-performance");
});
