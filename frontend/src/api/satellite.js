import { apiRequest } from "./client";

export const getSatelliteDamage = (latitude, longitude) => {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
  });
  return apiRequest(`/satellite/damage?${params.toString()}`);
};

export const getSatelliteNearby = (latitude, longitude, radius = 5000) => {
  const params = new URLSearchParams({
    latitude: String(latitude),
    longitude: String(longitude),
    radius: String(radius),
  });
  return apiRequest(`/satellite/nearby?${params.toString()}`);
};
