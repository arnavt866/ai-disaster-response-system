const SEVERITY_RANK = {
  Critical: 0,
  High: 1,
  Moderate: 2,
  Medium: 2,
  Low: 3,
};

function severityRank(severity) {
  return SEVERITY_RANK[severity] ?? 4;
}

function disasterIdKey(id) {
  return String(id);
}

/**
 * Pick a bounded set of disasters for map markers so the dashboard stays
 * responsive while always including the currently selected incident.
 */
export function pickMapDisasters(disasters, selectedDisasterId, limit = 120) {
  if (!Array.isArray(disasters) || disasters.length === 0) return [];

  const selectedKey =
    selectedDisasterId != null ? disasterIdKey(selectedDisasterId) : null;
  const selected = selectedKey
    ? disasters.find((item) => disasterIdKey(item.id) === selectedKey)
    : null;

  const ranked = [...disasters].sort((a, b) => {
    const severityDiff = severityRank(a.severity) - severityRank(b.severity);
    if (severityDiff !== 0) return severityDiff;
    const timeDiff =
      new Date(b.event_time || 0).getTime() - new Date(a.event_time || 0).getTime();
    if (timeDiff !== 0) return timeDiff;
    return Number(b.id) - Number(a.id);
  });

  const picked = [];
  const seen = new Set();

  if (selected) {
    picked.push(selected);
    seen.add(disasterIdKey(selected.id));
  }

  for (const disaster of ranked) {
    if (picked.length >= limit) break;
    const key = disasterIdKey(disaster.id);
    if (seen.has(key)) continue;
    picked.push(disaster);
    seen.add(key);
  }

  return picked;
}

export function sameDisasterId(a, b) {
  if (a == null || b == null) return false;
  return disasterIdKey(a) === disasterIdKey(b);
}
