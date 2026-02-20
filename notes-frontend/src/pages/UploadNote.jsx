import { useState } from "react";
import Layout from "../components/Layout";
import api from "../api/axios";
import toast from "react-hot-toast";

export default function UploadNote() {
  const [file, setFile] = useState(null);
  const [fileUrl, setFileUrl] = useState("");

  const [form, setForm] = useState({
    title: "",
    description: "",
    subject: "",
    unit: "",
    tags: "",
    note_type: "pdf",
    is_paid: false,
    price: 0,
  });

  const uploadFile = async () => {
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
      if (!fileUrl) return toast.error("Upload file first ❌");
      if (!form.title.trim()) return toast.error("Title required ❌");
      if (!form.subject.trim()) return toast.error("Subject required ❌");

      // ✅ paid note rules
      if (form.is_paid) {
        if (form.price < 50) return toast.error("Paid notes must start from ₹50");
        if (form.price > 150) return toast.error("Max price is ₹150");
      }

      const payload = {
        title: form.title,
        description: form.description,
        dept: "CSE", // ✅ auto (later take from user)
        semester: 3, // ✅ auto (later take from user)
        subject: form.subject,
        unit: String(form.unit || "1"),
        tags: form.tags
          ? form.tags.split(",").map((t) => t.trim()).filter(Boolean)
          : [],
        note_type: form.note_type,
        file_url: fileUrl,
        is_paid: form.is_paid,
        price: form.is_paid ? Number(form.price) : 0,
      };

      await api.post("/notes/", payload);
      toast.success("Note created ✅ Pending approval");

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
        is_paid: false,
        price: 0,
      });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Create note failed");
    }
  };

  return (
    <Layout title="Upload Note">
      <div className="max-w-3xl mx-auto">
        <div className="border border-black bg-white p-8 shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]">
          <h2 className="text-3xl font-black uppercase tracking-tighter text-black mb-8 border-b border-black pb-4">
            📤 Upload Notes
          </h2>

          {/* FILE UPLOAD */}
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
                  onClick={() => setForm({ ...form, is_paid: true, price: 50 })}
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
                    Set Price (₹50 - ₹150)
                  </label>
                  <input
                    type="number"
                    min={50}
                    max={150}
                    value={form.price}
                    onChange={(e) => {
                      let val = Number(e.target.value);
                      if (val > 150) val = 150;
                      if (val < 50) val = 50;
                      setForm({ ...form, price: val });
                    }}
                    className="w-full px-4 py-3 bg-white border border-black text-black font-bold text-lg"
                  />
                </div>
              )}
            </div>

            <button
              onClick={createNote}
              className="w-full mt-6 px-6 py-4 bg-black text-white border-2 border-black hover:bg-neutral-800 transition font-black uppercase tracking-wide text-lg shadow-[4px_4px_0px_0px_rgba(0,0,0,0.2)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]"
            >
              🚀 Publish Note
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
