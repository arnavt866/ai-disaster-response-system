const EARTH_RADIUS_KM = 6371;

export function formatRouteDistanceKm(distanceKm) {
  if (distanceKm == null) return "—";
  if (Number(distanceKm) === 0) return "Co-located (0 km)";
  return `${distanceKm} km`;
}

export function haversineKm(lat1, lon1, lat2, lon2) {
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const dPhi = ((lat2 - lat1) * Math.PI) / 180;
  const dLambda = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dPhi / 2) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLambda / 2) ** 2;
  return EARTH_RADIUS_KM * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function resolveRouteDepotId(
  allocation,
  selectedZoneId,
  depots,
  selectedZone,
  { maxFlowDepotDistanceKm = 100 } = {},
) {
  if (!Array.isArray(depots) || depots.length === 0) {
    return null;
  }

  const flowDepotId = allocation?.flows?.find(
    (flow) => flow.zone_id === selectedZoneId,
  )?.relief_center_id;

  if (flowDepotId != null && selectedZone) {
    const flowDepot = depots.find((depot) => depot.id === flowDepotId);
    if (flowDepot) {
      const flowDistance = haversineKm(
        selectedZone.latitude,
        selectedZone.longitude,
        flowDepot.latitude,
        flowDepot.longitude,
      );
      if (flowDistance <= maxFlowDepotDistanceKm) {
        return flowDepotId;
      }
    }
  } else if (flowDepotId != null) {
    return flowDepotId;
  }

  if (!selectedZone) {
    return depots[0].id;
  }

  let nearest = depots[0];
  let nearestDistance = haversineKm(
    selectedZone.latitude,
    selectedZone.longitude,
    nearest.latitude,
    nearest.longitude,
  );

  for (const depot of depots.slice(1)) {
    const distance = haversineKm(
      selectedZone.latitude,
      selectedZone.longitude,
      depot.latitude,
      depot.longitude,
    );
    if (distance < nearestDistance) {
      nearest = depot;
      nearestDistance = distance;
    }
  }

  return nearest.id;
}

export function routePolylinePositions(route) {
  const coordinates = route?.geometry?.coordinates;
  if (!Array.isArray(coordinates) || coordinates.length === 0) {
    return [];
  }

  return coordinates.map((coordinate) => {
    const [lon, lat] = coordinate;
    return [lat, lon];
  });
}

export function isRoadNetworkRoute(route) {
  return route?.routing_method === "road_network_local_osm";
}

export function getRouteOverlayLabel(route) {
  if (isRoadNetworkRoute(route)) {
    return "Road route";
  }
  return "Straight-line estimate (no road data for this area)";
}

export function getRoutePathOptions(route) {
  const blocked = route?.route_status === "blocked";
  const color = blocked ? "var(--critical)" : "var(--primary)";

  if (isRoadNetworkRoute(route)) {
    return { color, weight: 4 };
  }

  return { color, weight: 3, dashArray: "8 8" };
}

const MAX_ROUTE_BLOCK_POINTS = 8;

/**
 * OSM routes can have hundreds of tiny edges. Sample evenly along the
 * current path so operators can block a handful of points on the map.
 */
export function sampleRouteBlockPoints(route, maxPoints = MAX_ROUTE_BLOCK_POINTS) {
  const edges = Array.isArray(route?.path_edges) ? route.path_edges : [];
  const coordinates = Array.isArray(route?.geometry?.coordinates)
    ? route.geometry.coordinates
    : [];
  if (edges.length === 0 || coordinates.length < 2) return [];

  const count = Math.min(maxPoints, edges.length);
  if (count === 1) {
    const edge = edges[0];
    const a = coordinates[0];
    const b = coordinates[1] || a;
    return [{
      edge,
      index: 0,
      lat: (a[1] + b[1]) / 2,
      lon: (a[0] + b[0]) / 2,
    }];
  }

  const points = [];
  const seen = new Set();
  for (let i = 0; i < count; i += 1) {
    const idx = Math.round((i * (edges.length - 1)) / (count - 1));
    const key = `${edges[idx]?.region_id}:${edges[idx]?.u}:${edges[idx]?.v}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const a = coordinates[idx] || coordinates[0];
    const b = coordinates[idx + 1] || a;
    points.push({
      edge: edges[idx],
      index: idx,
      lat: (Number(a[1]) + Number(b[1])) / 2,
      lon: (Number(a[0]) + Number(b[0])) / 2,
    });
  }
  return points;
}
