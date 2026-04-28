interface Props {
  label: string;
  value: string | number;
  sublabel?: string;
}

export function PriceWidget({ label, value, sublabel }: Props) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-lg font-semibold text-white font-mono">{value}</span>
      {sublabel && <span className="text-xs text-gray-600">{sublabel}</span>}
    </div>
  );
}
