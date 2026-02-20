import Modal from "./Modal";
import Spinner from "./Spinner";
import FollowButton from "./FollowButton";
import { Link } from "react-router-dom";
import { API_BASE_URL } from "../api/baseUrl";

export default function PeopleModal({ open, onClose, title, loading, people }) {
  return (
    <Modal open={open} title={title} onClose={onClose}>
      {loading ? (
        <Spinner label="Loading..." />
      ) : people.length === 0 ? (
        <p className="text-gray-400 font-bold uppercase text-xs">No users found.</p>
      ) : (
        <div className="space-y-3">
          {people.map((p) => {
            const picUrl = p.profile_pic_url
              ? `${API_BASE_URL}${p.profile_pic_url}`
              : null;

            return (
              <div
                key={p.id}
                className="flex items-center justify-between gap-3 p-3 bg-white border border-gray-200 hover:border-black transition-colors"
              >
                <Link to={`/creator/${p.id}`} className="flex items-center gap-3">
                  <div className="w-10 h-10 border border-black bg-white flex items-center justify-center shrink-0">
                    {picUrl ? (
                      <img
                        src={picUrl}
                        alt="pic"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <span className="text-black font-bold text-sm">
                        {p.name?.[0]?.toUpperCase() || "U"}
                      </span>
                    )}
                  </div>

                  <div>
                    <p className="font-bold text-black uppercase tracking-wide text-sm">
                      {p.name} {p.verified_seller ? "✅" : ""}
                    </p>
                    <p className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">
                      {p.dept} • {p.year} • {p.section}
                    </p>
                  </div>
                </Link>

                <FollowButton creatorId={p.id} />
              </div>
            );
          })}
        </div>
      )}
    </Modal>
  );
}
