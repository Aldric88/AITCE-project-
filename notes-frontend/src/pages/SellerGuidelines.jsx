import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../auth/AuthContext";

const SECTIONS = [
  {
    id: "eligibility",
    title: "01 — Eligibility",
    icon: "🎓",
    rules: [
      "You must sign up with a valid college email address.",
      "Email OTP verification must be completed before uploading.",
      "Accounts that accumulate 5 AI violations lose upload access permanently.",
    ],
  },
  {
    id: "file",
    title: "02 — File Requirements",
    icon: "📄",
    rules: [
      "Accepted file types: PDF, Word Doc, PowerPoint, Image.",
      "PDFs must have selectable/readable text — blurry photo scans may be rejected.",
      "The file must contain enough academic content to be validated.",
      "Files must NOT contain personal information such as your email or phone number.",
      "Each file can only be linked to one note.",
    ],
  },
  {
    id: "content",
    title: "03 — Content Rules",
    icon: "📝",
    rules: [
      "Note content must genuinely match the subject and title you enter.",
      "No spam, gibberish, random characters, or filler text.",
      "No plagiarized content — only upload notes you wrote or co-authored.",
      "No offensive, political, adult, or non-academic material.",
      "Notes must be relevant to college-level academics.",
    ],
  },
  {
    id: "metadata",
    title: "04 — Metadata Accuracy",
    icon: "🏷️",
    rules: [
      "Title must clearly and accurately describe what the note covers.",
      "Subject must exactly match the actual content of the PDF.",
      "Department and semester must be correct.",
      "Tags must be relevant keywords from the note content.",
      "Mismatched metadata is a common reason for AI rejection.",
    ],
  },
  {
    id: "pricing",
    title: "05 — Pricing Rules",
    icon: "💰",
    rules: [
      "Free notes: set price to ₹0.",
      "Paid notes: minimum ₹1, maximum ₹150.",
      "Only verified sellers can upload paid notes.",
      "Price must reflect the genuine value of the content.",
    ],
  },
  {
    id: "ai",
    title: "06 — AI Moderation",
    icon: "🤖",
    rules: [
      "Every PDF upload is scanned by AI instantly — no human review queue.",
      "AI checks: content quality, subject relevance, spam score, and personal info.",
      "If your note passes → it is published immediately.",
      "If your note fails → you receive a specific rejection reason.",
      "Non-PDF files (doc, ppt, image, link, text) are auto-approved.",
    ],
  },
  {
    id: "violations",
    title: "07 — Violations & Consequences",
    icon: "⚠️",
    rules: [
      "Each AI rejection counts as 1 violation (shown as X/5 on your upload page).",
      "5 violations = permanent upload ban. You can still browse and buy notes.",
      "Only an admin can reset your violation count — contact support.",
      "Deliberately uploading spam or low-quality content repeatedly may result in account suspension.",
    ],
  },
];

const TIP_BOXES = [
  {
    icon: "✅",
    title: "Before you upload",
    tips: [
      "Open your PDF and make sure the text is selectable",
      "Double-check your subject matches the PDF content",
      "Remove any personal contact details from the file",
      "Write an accurate, descriptive title",
    ],
  },
  {
    icon: "❌",
    title: "Common rejection reasons",
    tips: [
      "PDF is a scanned image — text not extractable",
      "Subject says 'Data Structures' but PDF is about Networks",
      "PDF contains a phone number or email",
      "Content is too short or mostly blank",
    ],
  },
];

export default function SellerGuidelines() {
  const { user } = useAuth();
  const violations = user?.upload_violations ?? 0;
  const canUpload = user?.can_upload !== false;

  return (
    <Layout title="Seller Guidelines">
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="border-2 border-black dark:border-zinc-700 bg-black dark:bg-zinc-900 text-white p-8 mb-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,0.3)]">
          <p className="text-xs font-bold uppercase tracking-widest text-yellow-400 mb-2">Notes Market</p>
          <h1 className="text-4xl font-black uppercase tracking-tighter mb-3">Seller Guidelines</h1>
          <p className="text-gray-300 dark:text-zinc-400 text-sm leading-relaxed">
            Read these rules before uploading. Our AI moderates every note instantly —
            understanding these guidelines helps your notes get published without rejection.
          </p>
        </div>

        {/* Violation status bar */}
        {user && (
          <div className={`mb-8 p-4 border-2 font-bold text-sm uppercase tracking-wide flex items-center justify-between ${
            !canUpload
              ? "border-red-600 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-400"
              : violations > 0
              ? "border-yellow-500 bg-yellow-50 dark:bg-yellow-950 text-yellow-800 dark:text-yellow-400"
              : "border-green-500 bg-green-50 dark:bg-green-950 text-green-700 dark:text-green-400"
          }`}>
            <span>
              {!canUpload
                ? `⛔ Upload banned — ${violations} violations reached`
                : violations > 0
                ? `⚠️ Your violations: ${violations} / 5 — ${5 - violations} remaining`
                : "✅ Good standing — no violations"}
            </span>
            {canUpload && (
              <Link
                to="/upload-note"
                className="ml-4 px-4 py-1 bg-black dark:bg-white text-white dark:text-black text-xs font-black uppercase tracking-wide hover:bg-zinc-800 dark:hover:bg-zinc-100 transition"
              >
                Upload Note →
              </Link>
            )}
          </div>
        )}

        {/* Rules sections */}
        <div className="space-y-6 mb-10">
          {SECTIONS.map((section) => (
            <div key={section.id} className="group border border-black dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] dark:shadow-[4px_4px_0px_0px_rgba(255,255,255,0.05)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] dark:hover:shadow-[8px_8px_0px_0px_rgba(255,255,255,0.08)]">
              <div className="border-b border-black dark:border-zinc-700 px-6 py-3 bg-neutral-50 dark:bg-zinc-800 flex items-center gap-3">
                <span className="text-xl transition-transform duration-200 group-hover:scale-125 group-hover:rotate-6 inline-block">{section.icon}</span>
                <h2 className="font-black uppercase tracking-tight text-sm text-black dark:text-white">{section.title}</h2>
              </div>
              <ul className="px-6 py-4 space-y-3">
                {section.rules.map((rule, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-gray-800 dark:text-zinc-300 px-2 py-1 rounded transition-colors duration-150 hover:bg-neutral-50 dark:hover:bg-zinc-800">
                    <span className="mt-0.5 w-4 h-4 flex-shrink-0 border border-black dark:border-zinc-500 bg-black dark:bg-zinc-700 text-white flex items-center justify-center text-[9px] font-black">
                      {i + 1}
                    </span>
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Quick tips */}
        <div className="grid md:grid-cols-2 gap-6 mb-10">
          {TIP_BOXES.map((box) => (
            <div key={box.title} className="group border border-black dark:border-zinc-700 bg-white dark:bg-zinc-900 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] dark:shadow-[4px_4px_0px_0px_rgba(255,255,255,0.05)] transition-all duration-200 hover:-translate-y-1 hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] dark:hover:shadow-[8px_8px_0px_0px_rgba(255,255,255,0.08)]">
              <div className="border-b border-black dark:border-zinc-700 px-5 py-3 bg-neutral-50 dark:bg-zinc-800">
                <h3 className="font-black uppercase tracking-tight text-sm text-black dark:text-white">
                  <span className="inline-block transition-transform duration-200 group-hover:scale-125 mr-1">{box.icon}</span> {box.title}
                </h3>
              </div>
              <ul className="px-5 py-4 space-y-2">
                {box.tips.map((tip, i) => (
                  <li key={i} className="text-sm text-gray-700 dark:text-zinc-400 flex items-start gap-2 px-2 py-1 rounded transition-colors duration-150 hover:bg-neutral-50 dark:hover:bg-zinc-800">
                    <span className="text-gray-400 dark:text-zinc-600 mt-0.5">—</span>
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="border-2 border-black dark:border-zinc-700 p-6 flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-zinc-900 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] dark:shadow-[4px_4px_0px_0px_rgba(255,255,255,0.05)] mb-10 transition-all duration-200 hover:shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] dark:hover:shadow-[8px_8px_0px_0px_rgba(255,255,255,0.08)]">
          <div>
            <p className="font-black uppercase tracking-tight text-lg text-black dark:text-white">Ready to publish?</p>
            <p className="text-sm text-gray-600 dark:text-zinc-400">Follow the rules above and your note will be live instantly.</p>
          </div>
          <Link
            to="/upload-note"
            className="px-6 py-3 bg-black dark:bg-white text-white dark:text-black font-black uppercase tracking-wide text-sm border-2 border-black dark:border-white hover:bg-zinc-800 dark:hover:bg-zinc-100 transition-all duration-150 shadow-[4px_4px_0px_0px_rgba(0,0,0,0.4)] hover:shadow-none hover:translate-x-[4px] hover:translate-y-[4px] active:translate-x-[4px] active:translate-y-[4px] whitespace-nowrap"
          >
            🚀 Upload a Note
          </Link>
        </div>

      </div>
    </Layout>
  );
}
