export async function request(path, options) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) {
    const detail = result.detail;
    throw new Error(Array.isArray(detail)
      ? detail.map(error => error.msg).join(', ')
      : detail || `Request failed (${response.status})`);
  }
  return result;
}

export function datasetPath(id, action) {
  return `/datasets/${encodeURIComponent(id)}/${action}`;
}

export function safetyFor(profile = {}) {
  if (profile.ml_safety) return profile.ml_safety;
  const safe = profile.status === 'accept';
  const rules = profile.rules || [];
  return {
    safe_for_feature_retrieval: safe,
    decision: safe ? 'ALLOW' : 'BLOCK_PENDING_REPAIR',
    issue_count: rules.length,
    issues: rules.map(rule => ({
      column: rule.column || 'dataset',
      severity: rule.severity,
      characteristics: ['Quality rule failed'],
      recommended: 'Review source data',
      reason: rule.recommendation,
    })),
  };
}
