import { apiRequest } from "./client";

let cachedMetadata = null;
let pendingRequest = null;

export function getSystemMetadata({ refresh = false } = {}) {
  if (!refresh && cachedMetadata) {
    return Promise.resolve(cachedMetadata);
  }
  if (!refresh && pendingRequest) {
    return pendingRequest;
  }

  pendingRequest = apiRequest("/system/metadata")
    .then((data) => {
      cachedMetadata = data;
      pendingRequest = null;
      return data;
    })
    .catch((error) => {
      pendingRequest = null;
      throw error;
    });

  return pendingRequest;
}

export function demandTargetMaps(metadata) {
  const labels = {};
  const categories = {};
  (metadata?.demand_targets || []).forEach((entry) => {
    labels[entry.target] = entry.display_label;
    categories[entry.target] = entry.inventory_category;
  });
  return { labels, categories };
}
