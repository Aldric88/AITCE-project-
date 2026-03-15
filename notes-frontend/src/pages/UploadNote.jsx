import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";
import { useAuth } from "../auth/AuthContext";

export default function UploadNote() {
  const { user } = useAuth();
  const [file, setFile] = useState(null);
  const [fileUrl, setFileUrl] = useState("");

  const [form, setForm] = useState({
    title: "",
    description: "",
    subject: "",
    unit: "",
    tags: "",
    note_type: "pdf",
    external_link: "",
    is_paid: false,
    price: 0,
    dept: user?.dept || "",
    semester: Number(user?.year) > 0 ? Math.max(1, (Number(user.year) * 2) - 1) : 1,
  });

  const FILE_TYPES = ["pdf", "doc", "ppt", "image"];
  const NOTE_TYPE_OPTIONS = [
    { value: "pdf", label: "PDF" },
    { value: "doc", label: "Word Doc" },
    { value: "ppt", label: "PowerPoint" },
    { value: "image", label: "Image" },
    { value: "link", label: "External Link" },
    { value: "text", label: "Text Content" },
  ];
  const needsFileUpload = FILE_TYPES.includes(form.note_type);

  useEffect(() => {
    if (!user) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setForm((prev) => ({
      ...prev,
      dept: prev.dept || user.dept || "",
      semester: prev.semester || (Number(user.year) > 0 ? Math.max(1, (Number(user.year) * 2) - 1) : 1),
    }));
  }, [user]);

  const uploadFile = async () => {
    if (!needsFileUpload) return;
    if (!file) return toast.error("Choose a file first ❌");

    try {
      const fd = new FormData();
      fd.append("file", file);

      const res = await api.post("/files/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setFileUrl(res.data.file_url);
      toast.success("File uploaded ✅");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Upload failed");
    }
  };

  const createNote = async () => {
    try {
      if (!form.title.trim()) return toast.error("Title required ❌");
      if (!form.subject.trim()) return toast.error("Subject required ❌");

      if (needsFileUpload && !fileUrl) return toast.error("Upload file first ❌");
      if (form.note_type === "link" && !form.external_link.trim()) return toast.error("External link required ❌");
      if (form.note_type === "text" && !form.description.trim()) return toast.error("Text content (description) required ❌");

      // ✅ paid note rules
      if (form.is_paid) {
        if (form.price < 1) return toast.error("Paid notes must start from ₹1");
        if (form.price > 150) return toast.error("Max price is ₹150");
      }

      const payload = {
        title: form.title,
        description: form.description,
        dept: form.dept || user?.dept || "",
        semester: Number(form.semester) || 1,
        subject: form.subject,
        unit: String(form.unit || "1"),
        tags: form.tags
          ? form.tags.split(",").map((t) => t.trim()).filter(Boolean)
          : [],
        note_type: form.note_type,
        file_url: needsFileUpload ? fileUrl : undefined,
        external_link: form.note_type === "link" ? form.external_link.trim() : undefined,
        is_paid: form.is_paid,
        price: form.is_paid ? Number(form.price) : 0,
      };

      await api.post("/notes/", payload);
      toast.success("Note published ✅ AI approved your note!");

      // reset
      setFile(null);
      setFileUrl("");
      setForm({
        title: "",
        description: "",
        subject: "",
        unit: "",
        tags: "",
        note_type: "pdf",
        external_link: "",
        is_paid: false,
        price: 0,
        dept: user?.dept || "",
        semester: Number(user?.year) > 0 ? Math.max(1, (Number(user.year) * 2) - 1) : 1,
      });
    } catch (err) {
      const detail = err.response?.data?.detail || "Create note failed";
      toast.error(detail, { duration: 6000 });
    }
  };

  const violations = user?.upload_violations ?? 0;
  const canUpload = user?.can_upload !== false;

  return (
    <Layout title="Upload Note">
      <div className="max-w-3xl mx-auto">
        <div className="border border-black bg-white p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
          <h2 className="text-3xl font-black uppercase tracking-tighter text-black mb-4 border-b border-black pb-4">
            📤 Upload Notes
          </h2>

          {/* Upload ban warning */}
          {!canUpload && (
            <div className="mb-6 p-4 border-2 border-red-600 bg-red-50 text-red-700 font-bold uppercase text-sm tracking-wide">
              ⛔ You have been banned from uploading notes after {violations} violations. You can still browse and purchase notes.
            </div>
          )}

          {/* Seller guidelines nudge */}
          <div className="mb-5 p-3 border border-black dark:border-zinc-600 bg-neutral-50 dark:bg-zinc-800 text-sm flex items-center justify-between">
            <span className="text-gray-600 dark:text-zinc-400">First time uploading? Read the rules before you publish.</span>
            <Link to="/seller-guidelines" className="font-black uppercase text-xs tracking-wide underline hover:no-underline text-black dark:text-white">
              Seller Guidelines →
            </Link>
          </div>

          {/* Violation counter */}
          {canUpload && violations > 0 && (
            <div className="mb-6 p-3 border border-yellow-500 bg-yellow-50 text-yellow-800 text-sm font-bold uppercase tracking-wide">
              ⚠️ AI Violations: {violations} / 5 — {5 - violations} warning{5 - violations !== 1 ? "s" : ""} remaining before upload ban
            </div>
          )}

          {/* NOTE TYPE SELECTOR */}
          <div className="mb-6">
            <p className="font-bold uppercase tracking-wide text-sm mb-3">Note Type</p>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
              {NOTE_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setForm({ ...form, note_type: opt.value, external_link: "" })}
                  className={`px-3 py-2 text-xs font-black uppercase tracking-wide border transition-all ${
                    form.note_type === opt.value
                      ? "bg-black text-white border-black"
                      : "bg-white text-gray-500 border-gray-300 hover:border-black"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* FILE UPLOAD — only for file-based types */}
          {needsFileUpload && (
            <div className="border-2 border-dashed border-gray-300 bg-gray-50 p-6 mb-8 hover:border-black transition-colors">
              <p className="font-bold uppercase tracking-wide text-sm mb-4">Upload File</p>

              <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
                <input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full text-sm font-medium file:mr-4 file:py-2 file:px-4 file:border-0 file:text-sm file:font-bold file:bg-black file:text-white hover:file:bg-gray-800 file:uppercase file:tracking-wide file:cursor-pointer"
                />

                <button
                  onClick={uploadFile}
                  className="px-6 py-2 bg-black text-white hover:bg-neutral-800 transition font-bold uppercase tracking-wide text-sm whitespace-nowrap"
                >
                  Upload File
                </button>
              </div>

              <p className="text-xs font-bold uppercase tracking-wide text-gray-400 mt-4">
                Uploaded file_url:{" "}
                <span className="text-black bg-gray-200 px-1">
                  {fileUrl ? "✅ FILE READY" : "PENDING..."}
                </span>
              </p>
            </div>
          )}

          {/* EXTERNAL LINK — for link type */}
          {form.note_type === "link" && (
            <div className="border-2 border-dashed border-blue-200 bg-blue-50 p-6 mb-8">
              <p className="font-bold uppercase tracking-wide text-sm mb-3">External Link</p>
              <input
                className="w-full px-4 py-3 bg-white border border-black text-black focus:outline-none font-medium rounded-none"
                placeholder="https://drive.google.com/... or any URL"
                value={form.external_link}
                onChange={(e) => setForm({ ...form, external_link: e.target.value })}
              />
              <p className="text-xs text-blue-600 font-bold uppercase tracking-wide mt-2">
                Paste a Google Drive, OneDrive, or any public link to your notes
              </p>
            </div>
          )}

          {/* TEXT TYPE hint */}
          {form.note_type === "text" && (
            <div className="border-2 border-dashed border-emerald-200 bg-emerald-50 p-4 mb-6">
              <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">
                Text Note — use the Description field below to write your content
              </p>
            </div>
          )}

          {/* NOTE FORM */}
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">Note Title</label>
              <input
                className="w-full px-4 py-3 bg-white border border-black text-black focus:outline-none focus:ring-2 focus:ring-black transition-all font-bold rounded-none"
                placeholder="ENTER TITLE..."
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">Description</label>
              <textarea
                className="w-full px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all font-medium rounded-none text-black"
                placeholder="Enter description..."
                rows="4"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">Department</label>
                <input
                  className="w-full px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all font-bold rounded-none text-black"
                  placeholder="Department (ex: CSE)"
                  value={form.dept}
                  onChange={(e) => setForm({ ...form, dept: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">Semester</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  className="w-full px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all font-bold rounded-none text-black"
                  value={form.semester}
                  onChange={(e) => setForm({ ...form, semester: Number(e.target.value) || 1 })}
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">Subject</label>
                <input
                  className="w-full px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all font-bold rounded-none text-black"
                  placeholder="Subject (ex: DBMS)"
                  value={form.subject}
                  onChange={(e) => setForm({ ...form, subject: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">Unit</label>
                <input
                  className="w-full px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all font-bold rounded-none text-black"
                  placeholder="Unit (ex: 1)"
                  value={form.unit}
                  onChange={(e) => setForm({ ...form, unit: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">Tags</label>
              <input
                className="w-full px-4 py-3 bg-white border border-gray-300 focus:border-black focus:outline-none transition-all font-medium rounded-none text-black"
                placeholder="Tags (comma separated: ai,slides)"
                value={form.tags}
                onChange={(e) => setForm({ ...form, tags: e.target.value })}
              />
            </div>

            {/* Pricing */}
            <div className="border border-black p-6 bg-gray-50 mt-6">
              <p className="font-bold uppercase tracking-wide text-sm mb-4">Pricing Strategy</p>

              <div className="flex gap-4 mb-4">
                <button
                  type="button"
                  onClick={() => setForm({ ...form, is_paid: false, price: 0 })}
                  className={`flex-1 px-4 py-3 font-black uppercase tracking-wide text-sm border transition-all ${!form.is_paid
                      ? "bg-black text-white border-black"
                      : "bg-white text-gray-400 border-gray-300 hover:border-gray-400"
                    }`}
                >
                  Free Note
                </button>

                <button
                  type="button"
                  onClick={() => setForm({ ...form, is_paid: true, price: 1 })}
                  className={`flex-1 px-4 py-3 font-black uppercase tracking-wide text-sm border transition-all ${form.is_paid
                      ? "bg-black text-white border-black"
                      : "bg-white text-gray-400 border-gray-300 hover:border-gray-400"
                    }`}
                >
                  Paid Note
                </button>
              </div>

              {form.is_paid && (
                <div className="mt-3">
                  <label className="block text-xs font-bold uppercase tracking-wide text-gray-500 mb-1">
                    Set Price (₹1 - ₹150)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={150}
                    value={form.price}
                    onChange={(e) => {
                      let val = Number(e.target.value);
                      if (val > 150) val = 150;
                      if (val < 1) val = 1;
                      setForm({ ...form, price: val });
                    }}
                    className="w-full px-4 py-3 bg-white border border-black text-black font-bold text-lg"
                  />
                </div>
              )}
            </div>

            <button
              onClick={createNote}
              disabled={!canUpload}
              className={`w-full mt-6 px-6 py-4 border-2 font-black uppercase tracking-wide text-lg transition ${canUpload ? "bg-black text-white border-black hover:bg-neutral-800 shadow-[4px_4px_0px_0px_rgba(0,0,0,0.2)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]" : "bg-gray-300 text-gray-500 border-gray-300 cursor-not-allowed"}`}
            >
              {canUpload ? "🚀 Publish Note" : "⛔ Upload Banned"}
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
