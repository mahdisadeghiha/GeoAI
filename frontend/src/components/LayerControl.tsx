import type { LayerVisibility } from "../types";

interface LayerControlProps {
  layers: LayerVisibility;
  onChange: (layers: LayerVisibility) => void;
}

const LABELS: Record<keyof LayerVisibility, string> = {
  satellite2020: "Satellite 2020",
  satellite2025: "Satellite 2025",
  ndvi: "NDVI",
  changeDetection: "Change Detection",
  changeRegions: "Change Regions",
};

export function LayerControl({ layers, onChange }: LayerControlProps) {
  return (
    <div className="layer-control">
      <h3>Layers</h3>
      {(Object.keys(layers) as Array<keyof LayerVisibility>).map((key) => (
        <label key={key} className="layer-item">
          <input
            type="checkbox"
            checked={layers[key]}
            onChange={(e) => onChange({ ...layers, [key]: e.target.checked })}
          />
          {LABELS[key]}
        </label>
      ))}
    </div>
  );
}
