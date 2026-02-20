import { useCallback, useEffect, useState } from "react";
import api from "../api/axios";
import { API_BASE_URL } from "../api/baseUrl";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Comments({ noteId }) {
  const { user } = useAuth();

  const [threads, setThreads] = useState([]);
  const [text, setText] = useState("");
  const [posting, setPosting] = useState(false);
  const [replyingTo, setReplyingTo] = useState(null);
  const [replyText, setReplyText] = useState("");

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/comments/${noteId}`);
      setThreads(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load Q&A");
    }
  }, [noteId]);

  useEffect(() => {
    load();
  }, [load]);

  const postQuestion = async () => {
    if (!text.trim()) return toast.error("Type something first");

    try {
      setPosting(true);
      await api.post(`/comments/${noteId}`, { comment: text });
      setText("");
      toast.success("Posted");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to post");
    } finally {
      setPosting(false);
    }
  };

  const postReply = async () => {
    if (!replyText.trim()) return toast.error("Type reply first");
    if (!replyingTo) return;

    try {
      setPosting(true);
      await api.post(`/comments/${noteId}`, { comment: replyText, parent_id: replyingTo });
      setReplyText("");
      setReplyingTo(null);
      toast.success("Reply posted");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Reply failed");
    } finally {
      setPosting(false);
    }
  };

  const pinComment = async (commentId) => {
    try {
      await api.post(`/comments/${commentId}/pin`);
      toast.success("Pinned");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Pin failed");
    }
  };

  const unpinComment = async (commentId) => {
    try {
      await api.delete(`/comments/${commentId}/pin`);
      toast.success("Unpinned");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Unpin failed");
    }
  };

  const toggleLike = async (comment) => {
    try {
      if (comment.liked_by_me) {
        await api.delete(`/comments/${comment.id}/like`);
      } else {
        await api.post(`/comments/${comment.id}/like`);
      }
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Like action failed");
    }
  };

  const canPin = user?.role === "admin" || user?.role === "moderator";

  return (
    <div className="mt-8 border border-black bg-white p-6">
      <h3 className="mb-6 text-xl font-black uppercase tracking-wide">Doubts / Q&A</h3>

      {threads.length === 0 ? (
        <p className="text-sm font-bold uppercase tracking-wide text-gray-400">No doubts yet. Ask the first one.</p>
      ) : (
        <div className="space-y-6">
          {threads.map((t) => (
            <div key={t.id} className={`border p-4 transition-all ${t.is_pinned ? "border-black bg-yellow-50" : "border-gray-200 bg-white hover:border-black"}`}>
              <div className="flex items-start gap-4">
                <Link to={`/creator/${t.user?.id || ""}`} className="shrink-0">
                  <div className="flex h-10 w-10 items-center justify-center border border-black bg-gray-100">
                    {t.user?.profile_pic_url ? (
                      <img src={`${API_BASE_URL}${t.user.profile_pic_url}`} alt="pic" className="h-full w-full object-cover" />
                    ) : (
                      <span className="text-sm font-bold text-black">{t.user?.name?.[0]?.toUpperCase() || "U"}</span>
                    )}
                  </div>
                </Link>

                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <Link to={`/creator/${t.user?.id || ""}`} className="text-sm font-bold uppercase tracking-wide text-black hover:underline">
                        {t.user?.name} {t.user?.verified_seller ? "✓" : ""}
                      </Link>

                      <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wider text-gray-500">
                        {t.user?.dept} • {t.user?.year} • {t.user?.section}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleLike(t)}
                        className={`border px-2 py-1 text-xs font-bold uppercase transition ${
                          t.liked_by_me ? "border-black bg-black text-white" : "border-gray-300 bg-white text-black hover:border-black"
                        }`}
                      >
                        Like {t.likes_count}
                      </button>

                      {canPin &&
                        (!t.is_pinned ? (
                          <button onClick={() => pinComment(t.id)} className="border border-gray-300 bg-white px-2 py-1 text-xs font-bold uppercase transition hover:border-black">
                            Pin
                          </button>
                        ) : (
                          <button onClick={() => unpinComment(t.id)} className="border border-gray-300 bg-white px-2 py-1 text-xs font-bold uppercase transition hover:border-black">
                            Unpin
                          </button>
                        ))}
                    </div>
                  </div>

                  <p className="mt-2 text-sm leading-relaxed text-gray-800">{t.comment}</p>

                  <div className="mt-3 flex items-center gap-4 text-xs font-bold uppercase tracking-wide text-gray-400">
                    <span>{new Date(t.created_at * 1000).toLocaleString()}</span>
                    <button
                      onClick={() => {
                        setReplyingTo(t.id);
                        setReplyText("");
                      }}
                      className="hover:text-black hover:underline"
                    >
                      Reply
                    </button>
                  </div>

                  {replyingTo === t.id && (
                    <div className="mt-4 border-l-2 border-black pl-4">
                      <textarea
                        value={replyText}
                        onChange={(e) => setReplyText(e.target.value)}
                        className="w-full rounded-none border border-gray-200 bg-gray-50 px-4 py-3 text-sm transition-all focus:border-black focus:bg-white focus:outline-none"
                        placeholder="Write a reply..."
                        rows="2"
                      />

                      <div className="mt-2 flex gap-2">
                        <button onClick={postReply} disabled={posting} className="bg-black px-4 py-2 text-xs font-bold uppercase text-white transition hover:bg-neutral-800">
                          Post Reply
                        </button>

                        <button
                          onClick={() => {
                            setReplyingTo(null);
                            setReplyText("");
                          }}
                          className="border border-black px-4 py-2 text-xs font-bold uppercase text-black transition hover:bg-gray-100"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {t.replies?.length > 0 && (
                    <div className="mt-4 space-y-3 border-l border-gray-200 pl-4">
                      {t.replies.map((r) => (
                        <div key={r.id} className="border border-gray-100 bg-gray-50 p-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-start gap-3">
                              <Link to={`/creator/${r.user?.id || ""}`} className="shrink-0">
                                <div className="flex h-8 w-8 items-center justify-center border border-black bg-white">
                                  {r.user?.profile_pic_url ? (
                                    <img src={`${API_BASE_URL}${r.user.profile_pic_url}`} alt="pic" className="h-full w-full object-cover" />
                                  ) : (
                                    <span className="text-xs font-bold text-black">{r.user?.name?.[0]?.toUpperCase() || "U"}</span>
                                  )}
                                </div>
                              </Link>

                              <div>
                                <Link to={`/creator/${r.user?.id || ""}`} className="text-xs font-bold uppercase tracking-wide text-black hover:underline">
                                  {r.user?.name} {r.user?.verified_seller ? "✓" : ""}
                                </Link>

                                <p className="mt-0.5 text-[10px] font-bold uppercase text-gray-400">{new Date(r.created_at * 1000).toLocaleString()}</p>
                                <p className="mt-1 text-sm text-gray-700">{r.comment}</p>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 border-t border-gray-200 pt-4">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full rounded-none border border-gray-200 bg-white px-4 py-3 text-sm transition-all focus:border-black focus:outline-none"
          placeholder="Ask a doubt..."
          rows="3"
        />
        <div className="mt-2 flex justify-end">
          <button onClick={postQuestion} disabled={posting} className="btn-primary px-4 py-2 text-xs">
            Post
          </button>
        </div>
      </div>
    </div>
  );
}
