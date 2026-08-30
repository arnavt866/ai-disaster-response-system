/** Build mission resources_payload dict expected by backend schema. */
export function buildMissionResourcesPayload(allocation, zoneId) {
  if (!allocation || !Array.isArray(allocation.allocations)) {
    return null;
  }

  const items = allocation.allocations.filter((row) => row.zone_id === zoneId);
  const flows = Array.isArray(allocation.flows)
    ? allocation.flows.filter((row) => row.zone_id === zoneId)
    : [];

  return {
    run_id: allocation.run_id,
    zone_id: zoneId,
    coverage_ratio: allocation.coverage_ratio,
    items,
    flows,
  };
}
