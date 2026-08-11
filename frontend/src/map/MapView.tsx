import { GeoJSON, ImageOverlay, MapContainer, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";
import type { GeoJSONFeatureCollection, LayerVisibility } from "../types";

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
}

function FitBounds({ bbox }: { bbox: number[] }) {
  const map = useMap();
  useEffect(() => {
    if (bbox.length === 4) {
      map.fitBounds([
        [bbox[1], bbox[0]],
        [bbox[3], bbox[2]],
      ]);
    }
  }, [map, bbox]);
  return null;
}

function boundsFromBbox(bbox: number[]): [[number, number], [number, number]] {
  return [
    [bbox[1], bbox[0]],
    [bbox[3], bbox[2]],
  ];
}

export function MapView({ bbox, layers, runId, outputs, changeGeoJson }: MapViewProps) {
  const center: [number, number] = [(bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2];
  const bounds = boundsFromBbox(bbox);

  const onEachFeature = (feature: GeoJSON.Feature, layer: L.Layer) => {
    const props = feature.properties as Record<string, unknown>;
    if (props) {
      layer.bindPopup(
        `<strong>Region ${props.region_id}</strong><br/>Area: ${props.area_km2} km²<br/>Score: ${props.change_score}`
      );
    }
  };

  return (
    <MapContainer center={center} zoom={11} className="map-container" scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds bbox={bbox} />
      {runId && layers.satellite2020 && outputs.rgb_t1 && (
        <ImageOverlay url={outputs.rgb_t1} bounds={bounds} opacity={0.85} />
      )}
      {runId && layers.satellite2025 && outputs.rgb_t2 && (
        <ImageOverlay url={outputs.rgb_t2} bounds={bounds} opacity={0.85} />
      )}
      {runId && layers.ndvi && outputs.ndvi_diff && (
        <ImageOverlay url={outputs.ndvi_diff} bounds={bounds} opacity={0.7} />
      )}
      {runId && layers.changeDetection && outputs.change_mask && (
        <ImageOverlay url={outputs.change_mask} bounds={bounds} opacity={0.65} />
      )}
      {layers.changeRegions && changeGeoJson && (
        <GeoJSON data={changeGeoJson as GeoJSON.GeoJsonObject} onEachFeature={onEachFeature} />
      )}
    </MapContainer>
  );
}
