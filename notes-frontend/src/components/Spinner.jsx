export default function Spinner({ label = "Loading..." }) {
  return (
    <div className="flex items-center gap-3 text-zinc-300">
      <div className="w-5 h-5 border-2 border-zinc-500 border-t-transparent rounded-full animate-spin" />
      <span className="text-sm">{label}</span>
    </div>
  );
}
