import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useSymbolForecast } from "@/lib/hooks";
import { Brain, TrendingDown, TrendingUp } from "lucide-react";

const HORIZON_LABELS: Record<string, string> = { "1": "1 Day", "5": "1 Week", "21": "1 Month" };

/**
 * AI forecast for the symbol in the order ticket: expected return, 90% range,
 * and direction probability per horizon, with the model's honest out-of-sample
 * accuracy shown alongside.
 */
export function SymbolForecastCard({ symbol }: { symbol: string }) {
  const { data, isLoading, isError } = useSymbolForecast(symbol);

  if (!symbol) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" /> AI Forecast: {symbol.toUpperCase()}
        </CardTitle>
        {data?.success && (
          <CardDescription>
            {data.symbol && data.sector_etf
              ? <>Via {data.sector.replace(/_/g, " ")} model ({data.sector_etf}), beta {data.beta_to_sector}</>
              : <>Sector ensemble model · data through {data.as_of}</>}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid grid-cols-3 gap-3">
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
          </div>
        ) : isError || !data?.success ? (
          <p className="text-sm text-muted-foreground py-2">
            No forecast available for this symbol yet.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(data.horizons).map(([h, f]) => {
                const positive = f.expected_return_pct >= 0;
                return (
                  <div key={h} className="rounded-lg border border-border p-3">
                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">
                      {HORIZON_LABELS[h] || `${h}d`}
                    </div>
                    <div className={`flex items-center gap-1 text-lg font-bold tabular-nums ${positive ? "text-success" : "text-destructive"}`}>
                      {positive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                      {positive ? "+" : ""}{f.expected_return_pct.toFixed(2)}%
                    </div>
                    <div className="text-[11px] text-muted-foreground tabular-nums mt-0.5">
                      {f.ci_lower_pct.toFixed(1)}% … {f.ci_upper_pct.toFixed(1)}%
                    </div>
                    {f.prob_up != null && (
                      <div className="mt-2">
                        <div className="flex justify-between text-[10px] text-muted-foreground mb-0.5">
                          <span>P(up)</span>
                          <span className="tabular-nums">{Math.round(f.prob_up * 100)}%</span>
                        </div>
                        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full ${f.prob_up >= 0.5 ? "bg-success" : "bg-destructive"}`}
                            style={{ width: `${Math.round(f.prob_up * 100)}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="text-[11px] text-muted-foreground mt-3">
              Walk-forward validated ensemble (GBM + ARIMA + EGARCH + LSTM).
              Ranges are 90% intervals. Model v{data.model_version} — research tool, not advice.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
