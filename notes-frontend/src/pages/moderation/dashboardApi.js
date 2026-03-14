export async function fetchModerationBundle(api) {
  const [p, r, a, q, an, rl, ap, ct] = await Promise.allSettled([
    api.get("/notes/pending"),
    api.get("/notes/rejected"),
    api.get("/notes/approved"),
    api.get("/moderation/features/queue?limit=5"),
    api.get("/moderation/features/analytics?days=30"),
    api.get("/moderation/features/rules"),
    api.get("/moderation/features/appeals?status=open"),
    api.get("/moderation/features/confidence-trend?days=14"),
  ]);
  return { p, r, a, q, an, rl, ap, ct };
}

export async function fetchModerationInsights(api, noteId, uploaderId) {
  const requests = [
    api.get(`/moderation/features/explain/${noteId}`),
    api.get(`/moderation/features/quality-gate/check/${noteId}`),
    api.get(`/moderation/features/duplicates/${noteId}`),
    api.post(`/moderation/features/suggest-tags/${noteId}`),
    api.get(`/moderation/features/timeline/${noteId}`),
    api.get(`/moderation/features/diff/${noteId}`),
  ];
  if (uploaderId) {
    requests.push(api.get(`/moderation/features/creator-trust/${uploaderId}`));
  }
  const [explain, quality, duplicates, tags, timeline, diff, trust] = await Promise.allSettled(requests);
  return { explain, quality, duplicates, tags, timeline, diff, trust };
}
