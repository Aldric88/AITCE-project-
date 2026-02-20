export default function Spinner({ label = "Loading..." }) {
  return (
    <div className="flex items-center gap-3 text-black">
      <div className="w-5 h-5 border-2 border-gray-300 border-t-black rounded-full animate-spin" />
      <span className="text-xs font-bold uppercase tracking-wide">{label}</span>
    </div>
  );
}
