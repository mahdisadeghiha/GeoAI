import { GeoJSON, ImageOverlay, MapContainer, Rectangle, TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo } from "react";
import type { GeoJSONFeatureCollection, LayerVisibility } from "../types";
import { AoiDrawControl, type AoiBbox } from "./AoiDrawControl";

interface MapViewProps {
  bbox: number[];
  layers: LayerVisibility;
  runId: string | null;
  outputs: {
    rgb_t1?: string;
    rgb_t2?: string;
    ndvi_diff?: string;
    change_mask?: string;
  };
  changeGeoJson: GeoJSONFeatureCollection | null;
  drawEnabled: boolean;
  aoi: AoiBbox | null;
  onAoiChange: (aoi: AoiBbox | null) => void;
  analysisBbox?: number[] | null;
}

function FitBounds({ bbox, padding }: { bbox: number[]; padding?: number }) {
  const map = useMap();
  useEffect(() => {
    if (bbox.length === 4) {
      map.fitBounds(
        [
          [bbox[1], bbox[0]],
          [bbox[3], bbox[2]],
        ],
        { padding: [padding ?? 28, padding ?? 28], animate: true }
      );
    }
  }, [map, bbox, padding]);
  return null;
}

function boundsFromBbox(bbox: number[]): [[number, number], [number, number]] {
  return [
    [bbox[1], bbox[0]],
    [bbox[3], bbox[2]],
  ];
}

const regionStyle = {
  color: "#e0a045",
  weight: 2,
  fillColor: "#e06452",
  fillOpacity: 0.22,
  dashArray: undefined as string | undefined,
};

export function MapView({
  bbox,
  layers,
  runId,
  outputs,
  changeGeoJson,
  drawEnabled,
  aoi,
  onAoiChange,
  analysisBbox,
}: MapViewProps) {
  const center: [number, number] = [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2];
  const overlayBbox = analysisBbox && analysisBbox.length === 4 ? analysisBbox : aoi ?? bbox;
  const overlayBounds = boundsFromBbox(overlayBbox);
  const focusBbox = analysisBbox && analysisBbox.length === 4 ? analysisBbox : bbox;

  const activeOverlays = useMemo(() => {
    if (!runId) return [];
    const items: Array<{ key: string; url: string; opacity: number; zIndex: number }> = [];
    if (layers.satelliteT1 && outputs.rgb_t1) {
      items.push({ key: "sat1", url: outputs.rgb_t1, opacity: 0.92, zIndex: 410 });
    }
    if (layers.satelliteT2 && outputs.rgb_t2) {
      items.push({ key: "sat2", url: outputs.rgb_t2, opacity: 0.92, zIndex: 420 });
    }
    if (layers.ndvi && outputs.ndvi_diff) {
      items.push({ key: "ndvi", url: outputs.ndvi_diff, opacity: 0.78, zIndex: 430 });
    }
    if (layers.changeDetection && outputs.change_mask) {
      items.push({ key: "change", url: outputs.change_mask, opacity: 0.8, zIndex: 440 });
    }
    return items;
  }, [runId, layers, outputs]);

  const onEachFeature = (feature: GeoJSON.Feature, layer: L.Layer) => {
    const props = feature.properties as Record<string, unknown>;
    if (props) {
      layer.bindPopup(
        `<strong>Region ${props.region_id ?? "—"}</strong><br/>Area: ${props.area_km2 ?? "—"} km²<br/>Score: ${props.change_score ?? "—"}`
      );
    }
  };

  return (
    <MapContainer
      key={`${bbox.join(",")}`}
      center={center}
      zoom={11}
      className={`map-container${drawEnabled ? " draw-mode" : ""}`}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds bbox={focusBbox} />
      <Rectangle
        bounds={boundsFromBbox(bbox)}
        pathOptions={{ color: "#64748b", weight: 1, dashArray: "4 4", fillOpacity: 0 }}
      />
      {aoi && (
        <Rectangle
          bounds={boundsFromBbox(aoi)}
          pathOptions={{ color: "#3db8d0", weight: 2, dashArray: "2 4", fillOpacity: 0.05 }}
        />
      )}
      {analysisBbox && analysisBbox.length === 4 && (
        <Rectangle
          bounds={boundsFromBbox(analysisBbox)}
          pathOptions={{ color: "#e0a045", weight: 2, fillOpacity: 0 }}
        />
      )}
      <AoiDrawControl enabled={drawEnabled} aoi={aoi} onAoiChange={onAoiChange} />
      {activeOverlays.map((layer) => (
        <ImageOverlay
          key={`${runId}-${layer.key}-${layer.url}`}
          url={layer.url}
          bounds={overlayBounds}
          opacity={layer.opacity}
          zIndex={layer.zIndex}
        />
      ))}
      {layers.changeRegions && changeGeoJson && changeGeoJson.features.length > 0 && (
        <GeoJSON
          key={`${runId}-regions-${changeGeoJson.features.length}`}
          data={changeGeoJson as GeoJSON.GeoJsonObject}
          style={() => regionStyle}
          onEachFeature={onEachFeature}
        />
      )}
    </MapContainer>
  );
}
