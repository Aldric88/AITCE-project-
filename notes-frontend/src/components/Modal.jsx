export default function Modal({ open, title, onClose, children }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="border border-black bg-white max-w-2xl w-full max-h-[80vh] overflow-y-auto shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-6">
        <div className="flex items-center justify-between mb-6 border-b border-black pb-4">
          <h2 className="text-xl font-black uppercase tracking-wide text-black">{title}</h2>
          <button
            onClick={onClose}
            className="text-black hover:bg-gray-100 p-1 transition-colors border border-transparent hover:border-black"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
