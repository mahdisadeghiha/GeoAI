interface CompareItem {
  label: string;
  t1: number;
  t2: number;
  unit?: string;
  /** Prefer higher as positive (urban) or lower as positive (veg loss context) */
  invert?: boolean;
}

interface CompareBarsProps {
  title?: string;
  items: CompareItem[];
  yearT1?: number | string;
  yearT2?: number | string;
}

function scale(values: number[]): number {
  const max = Math.max(...values.map((v) => Math.abs(v)), 0.0001);
  return max;
}

export function CompareBars({ title, items, yearT1 = "T1", yearT2 = "T2" }: CompareBarsProps) {
  const all = items.flatMap((i) => [i.t1, i.t2]);
  const max = scale(all);

  return (
    <div className="compare-bars">
      {title && <h4 className="viz-title">{title}</h4>}
      <div className="compare-legend">
        <span>
          <i className="swatch t1" /> {yearT1}
        </span>
        <span>
          <i className="swatch t2" /> {yearT2}
        </span>
      </div>
      {items.map((item) => {
        const w1 = (Math.abs(item.t1) / max) * 100;
        const w2 = (Math.abs(item.t2) / max) * 100;
        const delta = item.t2 - item.t1;
        const up = item.invert ? delta < 0 : delta > 0;
        return (
          <div className="compare-row" key={item.label}>
            <div className="compare-meta">
              <span>{item.label}</span>
              <strong className={delta === 0 ? "flat" : up ? "up" : "down"}>
                {delta > 0 ? "+" : ""}
                {delta.toFixed(3)}
                {item.unit ?? ""}
              </strong>
            </div>
            <div className="bar-pair">
              <div className="bar-track">
                <div className="bar t1" style={{ width: `${w1}%` }} title={`${yearT1}: ${item.t1}`} />
              </div>
              <div className="bar-track">
                <div className="bar t2" style={{ width: `${w2}%` }} title={`${yearT2}: ${item.t2}`} />
              </div>
            </div>
            <div className="bar-values">
              <span>{item.t1.toFixed(3)}</span>
              <span>{item.t2.toFixed(3)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
