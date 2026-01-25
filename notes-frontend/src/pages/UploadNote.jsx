import { useState } from "react";
import api from "../api/axios";
import Layout from "../components/Layout";

export default function UploadNote() {
  const [file, setFile] = useState(null);

  const [note, setNote] = useState({
    title: "",
    description: "",
    dept: "CSE",
    semester: 3,
    subject: "AI",
    unit: "1",
    tags: "ai,slides",
    note_type: "pdf",
    is_paid: false,
    price: 0,
    file_url: "",
  });

  const uploadFile = async () => {
    if (!file) return alert("Choose a file first");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api.post("/files/upload", formData);
      setNote((p) => ({ ...p, file_url: res.data.file_url }));
      alert("File uploaded ✅");
    } catch (err) {
      alert(err.response?.data?.detail || "Upload failed");
    }
  };

  const createNote = async () => {
    if (!note.file_url) return alert("Upload file first");
    if (!note.title?.trim()) return alert("Title is required");

    const payload = {
      ...note,
      tags: note.tags ? note.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
    };

    try {
      await api.post("/notes/", payload);
      alert("Note created ✅ (Pending approval)");
    } catch (err) {
      alert(err.response?.data?.detail || "Create note failed");
    }
  };

  return (
    <Layout title="Upload Note">
      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
          <input
            type="file"
            accept=".pdf,.docx,.pptx,.jpg,.jpeg,.png"
            onChange={(e) => setFile(e.target.files?.[0])}
            className="block w-full text-sm text-zinc-300 file:mr-4 file:py-2 file:px-4
              file:rounded-xl file:border-0
              file:bg-zinc-800 file:text-zinc-100 hover:file:bg-zinc-700 transition"
          />

          <button
            onClick={uploadFile}
            className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition whitespace-nowrap"
          >
            Upload File
          </button>
        </div>

        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
            placeholder="Title"
            value={note.title}
            onChange={(e) => setNote({ ...note, title: e.target.value })}
          />
          <input
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
            placeholder="Subject"
            value={note.subject}
            onChange={(e) => setNote({ ...note, subject: e.target.value })}
          />
          <input
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
            placeholder="Unit"
            value={note.unit}
            onChange={(e) => setNote({ ...note, unit: e.target.value })}
          />
          <input
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500"
            placeholder="Tags (comma separated)"
            value={note.tags}
            onChange={(e) => setNote({ ...note, tags: e.target.value })}
          />
          <textarea
            className="px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-zinc-100 placeholder-zinc-500 md:col-span-2"
            placeholder="Description"
            value={note.description}
            onChange={(e) => setNote({ ...note, description: e.target.value })}
          />
        </div>

        <div className="mt-4 text-zinc-400">
          Uploaded file_url:{" "}
          <span className="text-zinc-200 font-medium">
            {note.file_url || "Not uploaded yet"}
          </span>
        </div>

        <button
          onClick={createNote}
          className="mt-6 px-5 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 transition"
        >
          Create Note
        </button>
      </div>
    </Layout>
  );
}
