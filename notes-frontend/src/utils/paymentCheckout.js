import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";

/**
 * Mock payment checkout for demo/resume purposes.
 * Simulates a successful INR payment without Razorpay.
 * In a production build, swap this for the Razorpay flow below.
 */
export async function checkoutPaidNote(note, options = {}) {
  const couponCode = (options.couponCode || "").trim().toUpperCase();
  const idempotencyKey = `${note.id}-mock-${Date.now()}-${crypto.randomUUID()}`;

  const res = await api.post(
    ENDPOINTS.payments.mockCheckout,
    { note_id: note.id, coupon_code: couponCode || undefined },
    { headers: { "X-Idempotency-Key": idempotencyKey } },
  );

  if (res.data?.message?.includes("Already purchased")) {
    return { alreadyPurchased: true };
  }

  return {
    paid: true,
    mock: true,
    amountPaid: res.data?.amount_paid,
    discountApplied: res.data?.discount_applied ?? 0,
  };
}

/**
 * Real Razorpay checkout — kept here for reference.
 * Uncomment and use this when you have real Razorpay credentials.
 *
 * export async function checkoutPaidNoteRazorpay(note, options = {}) {
 *   const couponCode = (options.couponCode || "").trim().toUpperCase();
 *   const idempotencyKey = `${note.id}-${Date.now()}-${crypto.randomUUID()}`;
 *   const orderRes = await api.post(
 *     ENDPOINTS.payments.createOrder,
 *     { note_id: note.id, coupon_code: couponCode || undefined },
 *     { headers: { "X-Idempotency-Key": idempotencyKey } },
 *   );
 *   if (orderRes.data?.message?.includes("Already purchased")) return { alreadyPurchased: true };
 *   const loaded = await loadRazorpayScript();
 *   if (!loaded) throw new Error("Razorpay SDK failed to load");
 *   await new Promise((resolve, reject) => {
 *     const rzp = new window.Razorpay({
 *       key: orderRes.data.key_id,
 *       amount: orderRes.data.amount,
 *       currency: orderRes.data.currency,
 *       name: "Notes Market",
 *       description: note.title,
 *       order_id: orderRes.data.order_id,
 *       handler: async (response) => {
 *         try {
 *           await api.post(ENDPOINTS.payments.verify, {
 *             note_id: note.id,
 *             razorpay_order_id: response.razorpay_order_id,
 *             razorpay_payment_id: response.razorpay_payment_id,
 *             razorpay_signature: response.razorpay_signature,
 *           }, { headers: { "X-Idempotency-Key": `${idempotencyKey}-verify` } });
 *           resolve(true);
 *         } catch (err) { reject(err); }
 *       },
 *       modal: { ondismiss: () => reject(new Error("Payment cancelled")) },
 *     });
 *     rzp.open();
 *   });
 *   return { paid: true };
 * }
 */
