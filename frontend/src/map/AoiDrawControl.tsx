import { useEffect, useRef } from "react";
import { Rectangle, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";

export type AoiBbox = [number, number, number, number]; // west, south, east, north

interface AoiDrawControlProps {
  enabled: boolean;
  aoi: AoiBbox | null;
  onAoiChange: (aoi: AoiBbox | null) => void;
}

function normalize(a: L.LatLng, b: L.LatLng): AoiBbox {
  return [
    Math.min(a.lng, b.lng),
    Math.min(a.lat, b.lat),
    Math.max(a.lng, b.lng),
    Math.max(a.lat, b.lat),
  ];
}

export function AoiDrawControl({ enabled, aoi, onAoiChange }: AoiDrawControlProps) {
  const map = useMap();
  const startRef = useRef<L.LatLng | null>(null);
  const previewRef = useRef<L.Rectangle | null>(null);

  useEffect(() => {
    if (enabled) {
      map.dragging.disable();
      map.getContainer().style.cursor = "crosshair";
    } else {
      map.dragging.enable();
      map.getContainer().style.cursor = "";
      if (previewRef.current) {
        map.removeLayer(previewRef.current);
        previewRef.current = null;
      }
      startRef.current = null;
    }
    return () => {
      map.dragging.enable();
      map.getContainer().style.cursor = "";
    };
  }, [enabled, map]);

  useMapEvents({
    mousedown(e) {
      if (!enabled) return;
      startRef.current = e.latlng;
      if (previewRef.current) {
        map.removeLayer(previewRef.current);
        previewRef.current = null;
      }
    },
    mousemove(e) {
      if (!enabled || !startRef.current) return;
      const bounds = L.latLngBounds(startRef.current, e.latlng);
      if (!previewRef.current) {
        previewRef.current = L.rectangle(bounds, {
          color: "#38bdf8",
          weight: 2,
          dashArray: "6 4",
          fillOpacity: 0.15,
        }).addTo(map);
      } else {
        previewRef.current.setBounds(bounds);
      }
    },
    mouseup(e) {
      if (!enabled || !startRef.current) return;
      const bbox = normalize(startRef.current, e.latlng);
      startRef.current = null;
      if (previewRef.current) {
        map.removeLayer(previewRef.current);
        previewRef.current = null;
      }
      // Ignore tiny accidental clicks
      if (Math.abs(bbox[2] - bbox[0]) < 0.0005 || Math.abs(bbox[3] - bbox[1]) < 0.0005) {
        return;
      }
      onAoiChange(bbox);
    },
  });

  if (!aoi) return null;
  const bounds: [[number, number], [number, number]] = [
    [aoi[1], aoi[0]],
    [aoi[3], aoi[2]],
  ];
  return (
    <Rectangle
      bounds={bounds}
      pathOptions={{ color: "#22d3ee", weight: 2, fillOpacity: 0.12 }}
    />
  );
}
