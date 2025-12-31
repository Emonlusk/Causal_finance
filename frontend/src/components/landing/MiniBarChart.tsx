interface MiniBarChartProps {
  traditional: number[];
  causal: number[];
  labels?: string[];
}

export function MiniBarChart({ traditional, causal, labels = ["Tech", "Health", "Energy"] }: MiniBarChartProps) {
  const maxValue = Math.max(...traditional, ...causal);

  return (
    <div className="h-16 flex items-end gap-2">
      {traditional.map((value, i) => (
        <div key={i} className="flex-1 flex flex-col items-center gap-1">
          <div className="w-full flex gap-0.5 items-end h-10">
            <div
              className="flex-1 bg-muted rounded-t transition-all duration-300 group-hover:bg-muted-foreground/30"
              style={{ height: `${(value / maxValue) * 100}%` }}
            />
            <div
              className="flex-1 bg-accent rounded-t transition-all duration-300"
              style={{ height: `${(causal[i] / maxValue) * 100}%` }}
            />
          </div>
          <span className="text-[10px] text-muted-foreground">{labels[i]}</span>
        </div>
      ))}
    </div>
  );
}
