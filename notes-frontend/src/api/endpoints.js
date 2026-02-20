export const ENDPOINTS = Object.freeze({
  notes: {
    list: "/notes",
    mine: "/notes/my",
    details: (noteId) => `/notes/${noteId}/details`,
    trending: "/notes/trending",
    semanticSearch: "/notes/semantic-search",
    versions: (noteId) => `/notes/${noteId}/versions`,
    confidence: (noteId) => `/notes/${noteId}/confidence`,
  },
  purchases: {
    buy: (noteId) => `/purchase/${noteId}`,
    mine: "/purchase/my",
    has: (noteId) => `/purchase/has/${noteId}`,
  },
  payments: {
    createOrder: "/payments/create-order",
    verify: "/payments/verify",
  },
  bundles: {
    list: "/bundles",
    create: "/bundles",
  },
  library: {
    mine: "/library/my",
  },
  bookmarks: {
    mine: "/bookmarks/my",
    byNote: (noteId) => `/bookmarks/${noteId}`,
  },
  likes: {
    mine: "/likes/my",
    byNote: (noteId) => `/likes/${noteId}`,
  },
  reviews: {
    note: (noteId) => `/reviews/note/${noteId}`,
  },
  recommendations: {
    alsoBought: (noteId) => `/recommendations/also-bought/${noteId}`,
  },
  ai: {
    workerHealth: "/ai/worker/health",
  },
  notifications: {
    list: "/notifications",
    unreadCount: "/notifications/unread-count",
    readAll: "/notifications/read-all",
    readOne: (notificationId) => `/notifications/${notificationId}/read`,
    stream: "/notifications/stream",
    preferences: "/notifications/preferences",
    digest: "/notifications/digest",
  },
  ops: {
    health: "/ops/health",
    runtime: "/ops/runtime",
  },
  requests: {
    list: "/requests",
    create: "/requests",
    close: (requestId) => `/requests/${requestId}/close`,
    vote: (requestId) => `/requests/${requestId}/vote`,
    heatmap: "/requests/insights/demand-heatmap",
  },
  spaces: {
    mine: "/spaces/my",
    create: "/spaces",
    join: (inviteCode) => `/spaces/join/${inviteCode}`,
    announcements: (spaceId) => `/spaces/${spaceId}/announcements`,
  },
  monetization: {
    couponsCreate: "/monetization/coupons",
    couponsMine: "/monetization/coupons/my",
    couponsApply: "/monetization/coupons/apply",
    campaignsCreate: "/monetization/campaigns",
    campaignsMine: "/monetization/campaigns/my",
    payoutsMine: "/monetization/payouts/me",
  },
  admin: {
    analyticsFunnel: "/admin/analytics/funnel",
    domainCandidates: "/admin/domain-candidates",
    approveDomainCandidate: (domain) => `/admin/domain-candidates/${encodeURIComponent(domain)}/approve`,
    rejectDomainCandidate: (domain) => `/admin/domain-candidates/${encodeURIComponent(domain)}/reject`,
  },
  risk: {
    me: "/risk/me",
    users: "/risk/users",
  },
  downloads: {
    note: (noteId) => `/download/${noteId}`,
  },
});
