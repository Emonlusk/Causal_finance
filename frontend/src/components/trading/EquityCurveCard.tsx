import { useMemo } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolioEquityCurve } from "@/lib/hooks";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { LineChart as LineChartIcon } from "lucide-react";

export function EquityCurveCard({ portfolioId }: { portfolioId: number }) {
  const { data, isLoading } = usePortfolioEquityCurve(portfolioId);

  const points = useMemo(
    () =>
      (data?.equity_curve || []).map((p) => ({
        date: p.date,
        equity: p.equity,
      })),
    [data]
  );

  const change = useMemo(() => {
    if (points.length < 2) return null;
    const first = points[0].equity;
    const last = points[points.length - 1].equity;
    if (!first) return null;
    return { abs: last - first, pct: ((last - first) / first) * 100 };
  }, [points]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <LineChartIcon className="w-4 h-4 text-primary" /> Equity Curve
            </CardTitle>
            <CardDescription>Total portfolio value over time (daily snapshots)</CardDescription>
          </div>
          {change && (
            <div className={`text-sm font-semibold tabular-nums ${change.abs >= 0 ? "text-success" : "text-destructive"}`}>
              {change.abs >= 0 ? "+" : ""}${Math.abs(change.abs).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              <span className="text-xs ml-1">({change.pct >= 0 ? "+" : ""}{change.pct.toFixed(2)}%)</span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : points.length < 2 ? (
          <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
            Snapshots build up daily — trade and check back tomorrow to see your curve.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={192}>
            <AreaChart data={points} margin={{ top: 6, right: 6, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                minTickGap={40}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                width={70}
                domain={["auto", "auto"]}
                tickFormatter={(v: number) => `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                  fontSize: 12,
                }}
                formatter={(v: number) => [`$${v.toLocaleString(undefined, { minimumFractionDigits: 2 })}`, "Equity"]}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                fill="url(#equityFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
