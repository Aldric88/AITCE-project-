import api from "../api/axios";
import { ENDPOINTS } from "../api/endpoints";

let razorpayLoader = null;

function loadRazorpayScript() {
  if (window.Razorpay) return Promise.resolve(true);
  if (razorpayLoader) return razorpayLoader;

  razorpayLoader = new Promise((resolve) => {
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });

  return razorpayLoader;
}

export async function checkoutPaidNote(note, options = {}) {
  const couponCode = (options.couponCode || "").trim().toUpperCase();
  const idempotencyKey = `${note.id}-${Date.now()}-${crypto.randomUUID()}`;
  const orderRes = await api.post(
    ENDPOINTS.payments.createOrder,
    { note_id: note.id, coupon_code: couponCode || undefined },
    { headers: { "X-Idempotency-Key": idempotencyKey } },
  );
  if (orderRes.data?.message && orderRes.data?.message.includes("Already purchased")) {
    return { alreadyPurchased: true };
  }

  const loaded = await loadRazorpayScript();
  if (!loaded || !window.Razorpay) {
    throw new Error("Razorpay SDK failed to load");
  }

  await new Promise((resolve, reject) => {
    const rzp = new window.Razorpay({
      key: orderRes.data.key_id,
      amount: orderRes.data.amount,
      currency: orderRes.data.currency,
      name: "Notes Market",
      description: note.title || orderRes.data.note_title || "Note purchase",
      order_id: orderRes.data.order_id,
      prefill: {
        name: orderRes.data.user_name || "",
        email: orderRes.data.user_email || "",
      },
      handler: async (response) => {
        try {
          await api.post(
            ENDPOINTS.payments.verify,
            {
              note_id: note.id,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            },
            {
              headers: {
                "X-Idempotency-Key": `${idempotencyKey}-verify`,
              },
            },
          );
          resolve(true);
        } catch (err) {
          reject(
            new Error(err?.response?.data?.detail || "Payment verification failed"),
          );
        }
      },
      modal: {
        ondismiss: () => reject(new Error("Payment cancelled")),
      },
    });
    rzp.open();
  });

  return { paid: true };
}
