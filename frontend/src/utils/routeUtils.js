const EARTH_RADIUS_KM = 6371;

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
