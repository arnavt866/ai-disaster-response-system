import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";

export default function FitRouteBounds({ positions }) {
  const map = useMap();

  useEffect(() => {
    if (!positions?.length) {
      return undefined;
    }

    const bounds = L.latLngBounds(positions);
    map.fitBounds(bounds, { padding: [24, 24] });
    return undefined;
  }, [map, positions]);

  return null;
}
