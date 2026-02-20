export default function SkeletonCard() {
  return (
    <div className="minimal-card animate-pulse p-6">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="mb-2 h-6 w-3/4 bg-gray-200" />
          <div className="h-4 w-1/2 bg-gray-100" />
        </div>
        <div className="h-8 w-16 bg-gray-200" />
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <div className="h-4 w-16 bg-gray-100" />
        <div className="h-4 w-16 bg-gray-100" />
        <div className="h-4 w-20 bg-gray-100" />
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <div className="h-6 w-24 bg-gray-100" />
        <div className="h-6 w-28 bg-gray-100" />
      </div>

      <div className="mb-4 flex items-center gap-3 border-b border-gray-100 pb-3">
        <div className="flex-1">
          <div className="mb-1 h-3 w-20 bg-gray-100" />
          <div className="h-4 w-32 bg-gray-200" />
        </div>
        <div className="text-right">
          <div className="mb-1 h-3 w-16 bg-gray-100" />
          <div className="h-4 w-20 bg-gray-200" />
        </div>
      </div>

      <div className="mb-6 space-y-2">
        <div className="h-4 w-full bg-gray-100" />
        <div className="h-4 w-5/6 bg-gray-100" />
      </div>

      <div className="mb-6 flex items-center justify-between border-t border-gray-100 pt-4">
        <div className="h-4 w-16 bg-gray-100" />
        <div className="h-4 w-16 bg-gray-100" />
        <div className="h-4 w-16 bg-gray-100" />
      </div>

      <div className="space-y-3">
        <div className="h-12 bg-gray-200" />
        <div className="h-10 bg-gray-100" />
        <div className="grid grid-cols-3 gap-2">
          <div className="h-10 bg-gray-100" />
          <div className="h-10 bg-gray-100" />
          <div className="h-10 bg-gray-100" />
        </div>
      </div>
    </div>
  );
}
