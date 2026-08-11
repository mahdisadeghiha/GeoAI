import type { LayerVisibility } from "../types";

interface LayerControlProps {
  layers: LayerVisibility;
  onChange: (layers: LayerVisibility) => void;
  yearT1: number;
  yearT2: number;
  disabled?: boolean;
}

const META: Record<
  keyof LayerVisibility,
  { icon: string; tone: string }
> = {
  satelliteT1: { icon: "◉", tone: "sky" },
  satelliteT2: { icon: "◎", tone: "teal" },
  ndvi: { icon: "∿", tone: "teal" },
  changeDetection: { icon: "▣", tone: "amber" },
  changeRegions: { icon: "⬡", tone: "coral" },
};

export function LayerControl({
  layers,
  onChange,
  yearT1,
  yearT2,
  disabled = false,
}: LayerControlProps) {
  const labels: Record<keyof LayerVisibility, string> = {
    satelliteT1: `Satellite ${yearT1}`,
    satelliteT2: `Satellite ${yearT2}`,
    ndvi: "NDVI Difference",
    changeDetection: "Change Detection",
    changeRegions: "Change Regions",
  };

  return (
    <div className="layer-control">
      <div className="layer-head">
        <h3>Map Layers</h3>
        <span className="muted">{disabled ? "Run analysis to enable" : "Toggle overlays"}</span>
      </div>
      <div className="layer-grid">
        {(Object.keys(layers) as Array<keyof LayerVisibility>).map((key) => {
          const on = layers[key];
          const isRaster = key !== "changeRegions";
          const locked = Boolean(disabled && isRaster);
          return (
            <button
              key={key}
              type="button"
              className={`layer-chip ${META[key].tone}${on ? " on" : ""}${locked ? " locked" : ""}`}
              onClick={() => {
                if (locked) return;
                onChange({ ...layers, [key]: !on });
              }}
              aria-pressed={on}
              disabled={locked}
              title={locked ? "Run analysis first to load imagery overlays" : labels[key]}
            >
              <span className="layer-icon" aria-hidden>
                {META[key].icon}
              </span>
              <span>{labels[key]}</span>
              <span className={`toggle-dot${on ? " on" : ""}`} />
            </button>
          );
        })}
      </div>
    </div>
  );
}
