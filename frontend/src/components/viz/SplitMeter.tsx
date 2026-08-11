interface SplitMeterProps {
  title: string;
  leftLabel: string;
  rightLabel: string;
  leftValue: number;
  rightValue: number;
  leftTone?: string;
  rightTone?: string;
  unit?: string;
}

export function SplitMeter({
  title,
  leftLabel,
  rightLabel,
  leftValue,
  rightValue,
  leftTone = "teal",
  rightTone = "amber",
  unit = "%",
}: SplitMeterProps) {
  const total = Math.abs(leftValue) + Math.abs(rightValue) || 1;
  const leftPct = (Math.abs(leftValue) / total) * 100;
  const rightPct = (Math.abs(rightValue) / total) * 100;

  return (
    <div className="split-meter">
      <div className="split-head">
        <h4 className="viz-title">{title}</h4>
        <span className="split-total">
          {leftValue.toFixed(1)}
          {unit} / {rightValue.toFixed(1)}
          {unit}
        </span>
      </div>
      <div className="split-track">
        <div className={`split-seg ${leftTone}`} style={{ width: `${leftPct}%` }} />
        <div className={`split-seg ${rightTone}`} style={{ width: `${rightPct}%` }} />
      </div>
      <div className="split-labels">
        <span>
          <i className={`dot ${leftTone}`} /> {leftLabel}
        </span>
        <span>
          <i className={`dot ${rightTone}`} /> {rightLabel}
        </span>
      </div>
    </div>
  );
}
