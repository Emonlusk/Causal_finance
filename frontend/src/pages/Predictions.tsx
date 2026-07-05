import { useMemo, useState } from "react";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Brain, Info, Table2, BarChartHorizontal, Activity, RefreshCw } from "lucide-react";
import { useAllForecasts, useCurrentRegime, useMarketCondition } from "@/lib/hooks";
import type { HorizonForecast } from "@/lib/api";

const HORIZON_LABELS: Record<string, string> = {
  "1": "1 Day",
  "5": "1 Week",
  "21": "1 Month",
};

const SECTOR_LABELS: Record<string, string> = {
  Technology: "Technology",
  Healthcare: "Healthcare",
  Energy: "Energy",
  Financials: "Financials",
  Industrials: "Industrials",
  Consumer_Discretionary: "Consumer Discretionary",
  Consumer_Staples: "Consumer Staples",
  Utilities: "Utilities",
  Materials: "Materials",
  Real_Estate: "Real Estate",
  Communication_Services: "Communication Services",
};

const REGIME_LABELS: Record<string, { label: string; tone: string }> = {
  bull: { label: "Bull Market", tone: "text-success" },
  bear: { label: "Bear Market", tone: "text-destructive" },
  sideways: { label: "Sideways", tone: "text-warning" },
  crisis: { label: "Crisis", tone: "text-destructive" },
  high_volatility: { label: "High Volatility", tone: "text-warning" },
};

interface SectorRow {
  sector: string;
  etf: string;
  asOf: string;
  f: HorizonForecast;
}

/** Dot-and-band range chart row: CI band + expected-value dot on a shared scale. */
function ForecastRangeRow({
  row,
  domain,
  expanded,
  onToggle,
}: {
  row: SectorRow;
  domain: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { f } = row;
  const pct = (v: number) => 50 + (v / domain) * 50; // -domain..+domain -> 0..100
  const left = Math.max(0, Math.min(100, pct(f.ci_lower_pct)));
  const right = Math.max(0, Math.min(100, pct(f.ci_upper_pct)));
  const dot = Math.max(0, Math.min(100, pct(f.expected_return_pct)));
  const positive = f.expected_return_pct >= 0;
  const probUp = f.prob_up != null ? Math.round(f.prob_up * 100) : null;
  const dirAcc = f.validation?.gbm_dir ?? f.validation?.clf_dir;

  return (
    <div
      className="group rounded-lg px-2 py-1.5 hover:bg-muted/50 cursor-pointer transition-colors"
      onClick={onToggle}
      role="button"
      aria-expanded={expanded}
    >
      <div className="grid grid-cols-[11rem_1fr_5.5rem_5rem] items-center gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium truncate">{SECTOR_LABELS[row.sector] || row.sector}</span>
          <Badge variant="outline" className="text-[10px] px-1 py-0 shrink-0">{row.etf}</Badge>
        </div>

        {/* Range band with zero axis */}
        <div className="relative h-6" aria-label={`Expected ${f.expected_return_pct}%, 90% CI ${f.ci_lower_pct}% to ${f.ci_upper_pct}%`}>
          <div className="absolute inset-y-1.5 left-0 right-0 rounded-full bg-muted/60" />
          <div className="absolute inset-y-0 w-px bg-border" style={{ left: "50%" }} />
          <div
            className={`absolute inset-y-1.5 rounded-full ${positive ? "bg-success/25" : "bg-destructive/25"}`}
            style={{ left: `${Math.min(left, right)}%`, width: `${Math.max(Math.abs(right - left), 1)}%` }}
          />
          <div
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2.5 h-2.5 rounded-full ring-2 ring-background ${positive ? "bg-success" : "bg-destructive"}`}
            style={{ left: `${dot}%` }}
          />
        </div>

        <div className={`text-sm font-semibold tabular-nums text-right ${positive ? "text-success" : "text-destructive"}`}>
          {positive ? "+" : ""}{f.expected_return_pct.toFixed(2)}%
        </div>

        <div className="text-right">
          {probUp != null ? (
            <span className="text-xs text-muted-foreground tabular-nums">{probUp}% ↑</span>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          )}
        </div>
      </div>

      {expanded && (
        <div className="mt-2 ml-1 grid gap-2 text-xs text-muted-foreground border-l-2 border-border pl-3 pb-1">
          <div>
            90% interval: <span className="text-foreground tabular-nums">{f.ci_lower_pct.toFixed(2)}% to {f.ci_upper_pct.toFixed(2)}%</span>
            {" · "}volatility <span className="text-foreground tabular-nums">{f.volatility_pct.toFixed(2)}%</span>
          </div>
          {f.model_predictions_pct && (
            <div className="flex flex-wrap gap-x-4 gap-y-1">
              {Object.entries(f.model_predictions_pct).map(([model, v]) => (
                <span key={model}>
                  {model.toUpperCase()}: <span className="text-foreground tabular-nums">{v >= 0 ? "+" : ""}{v.toFixed(2)}%</span>
                  {f.ensemble_weights?.[model] != null && (
                    <span className="opacity-70"> (w={f.ensemble_weights[model]})</span>
                  )}
                </span>
              ))}
            </div>
          )}
          {dirAcc != null && (
            <div>
              Walk-forward direction accuracy: <span className="text-foreground tabular-nums">{(dirAcc * 100).toFixed(1)}%</span>
              <span className="opacity-70"> (out-of-sample; 50% = coin flip)</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const Predictions = () => {
  const [horizon, setHorizon] = useState<"1" | "5" | "21">("21");
  const [view, setView] = useState<"chart" | "table">("chart");
  const [expandedSector, setExpandedSector] = useState<string | null>(null);
  const { data, isLoading, isError, refetch, isFetching } = useAllForecasts();
  const { data: regimeData } = useCurrentRegime();
  const { data: conditionData } = useMarketCondition();

  const rows: SectorRow[] = useMemo(() => {
    const forecasts = data?.forecasts || {};
    return Object.entries(forecasts)
      .map(([sector, f]) => ({
        sector,
        etf: f.etf,
        asOf: f.as_of,
        f: f.horizons?.[horizon],
      }))
      .filter((r): r is SectorRow => !!r.f)
      .sort((a, b) => b.f.expected_return_pct - a.f.expected_return_pct);
  }, [data, horizon]);

  const domain = useMemo(() => {
    const maxAbs = Math.max(1, ...rows.flatMap((r) => [Math.abs(r.f.ci_lower_pct), Math.abs(r.f.ci_upper_pct)]));
    return maxAbs * 1.05;
  }, [rows]);

  const modelVersion = useMemo(() => {
    const first = Object.values(data?.forecasts || {})[0];
    return first?.model_version;
  }, [data]);

  const regime = regimeData?.regime?.current_regime;
  const regimeStyle = regime ? REGIME_LABELS[regime] || { label: regime, tone: "text-foreground" } : null;
  const regimeProb = regimeData?.regime?.regime_probability;
  const condition = conditionData?.condition;

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-5xl">
        {/* Context row */}
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <Activity className="w-3.5 h-3.5" /> Market Regime (HMM)
              </div>
              {regimeStyle ? (
                <>
                  <div className={`text-xl font-bold ${regimeStyle.tone}`}>{regimeStyle.label}</div>
                  {regimeProb != null && (
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {(regimeProb * 100).toFixed(0)}% probability
                    </div>
                  )}
                </>
              ) : (
                <Skeleton className="h-7 w-28" />
              )}
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <Info className="w-3.5 h-3.5" /> Market Condition
              </div>
              {condition ? (
                <>
                  <div className={`text-xl font-bold capitalize ${
                    condition.state === "bullish" ? "text-success" :
                    condition.state === "bearish" ? "text-destructive" : "text-warning"
                  }`}>{condition.state}</div>
                  <div className="text-xs text-muted-foreground mt-0.5 truncate">{condition.factors?.[0]}</div>
                </>
              ) : (
                <Skeleton className="h-7 w-24" />
              )}
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                <Brain className="w-3.5 h-3.5" /> Forecast Model
              </div>
              <div className="text-sm font-semibold">GBM + ARIMA + EGARCH + LSTM</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Walk-forward validated{modelVersion ? ` · v${modelVersion}` : ""}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Forecast card */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle className="text-lg">Sector Return Forecasts</CardTitle>
                <CardDescription>
                  Expected return with 90% interval and probability of a positive move
                  {rows[0]?.asOf ? ` · data through ${rows[0].asOf}` : ""}
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Tabs value={horizon} onValueChange={(v) => setHorizon(v as typeof horizon)}>
                  <TabsList className="h-8">
                    {Object.entries(HORIZON_LABELS).map(([h, label]) => (
                      <TabsTrigger key={h} value={h} className="text-xs px-3 h-6">{label}</TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline" size="icon" className="h-8 w-8"
                      onClick={() => setView(view === "chart" ? "table" : "chart")}
                      aria-label="Toggle table view"
                    >
                      {view === "chart" ? <Table2 className="w-4 h-4" /> : <BarChartHorizontal className="w-4 h-4" />}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>{view === "chart" ? "Table view" : "Chart view"}</TooltipContent>
                </Tooltip>
                <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => refetch()} aria-label="Refresh forecasts">
                  <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-8 w-full" />)}
              </div>
            ) : isError || rows.length === 0 ? (
              <div className="text-center py-10 text-muted-foreground text-sm">
                <p className="font-medium mb-1">No trained forecast models found</p>
                <p>Run <code className="bg-muted px-1.5 py-0.5 rounded">python -m scripts.train_models</code> in the backend to train them.</p>
              </div>
            ) : view === "chart" ? (
              <div>
                {/* Column headers */}
                <div className="grid grid-cols-[11rem_1fr_5.5rem_5rem] gap-3 px-2 pb-2 text-[11px] uppercase tracking-wide text-muted-foreground">
                  <span>Sector</span>
                  <span className="text-center">Forecast range ({HORIZON_LABELS[horizon]})</span>
                  <span className="text-right">Expected</span>
                  <span className="text-right">P(up)</span>
                </div>
                <div className="space-y-0.5">
                  {rows.map((row) => (
                    <ForecastRangeRow
                      key={row.sector}
                      row={row}
                      domain={domain}
                      expanded={expandedSector === row.sector}
                      onToggle={() => setExpandedSector(expandedSector === row.sector ? null : row.sector)}
                    />
                  ))}
                </div>
                {/* Axis labels */}
                <div className="grid grid-cols-[11rem_1fr_5.5rem_5rem] gap-3 px-2 pt-1">
                  <span />
                  <div className="flex justify-between text-[10px] text-muted-foreground tabular-nums">
                    <span>-{domain.toFixed(0)}%</span><span>0</span><span>+{domain.toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-muted-foreground border-b border-border">
                      <th className="py-2 pr-3 font-medium">Sector</th>
                      <th className="py-2 px-3 font-medium text-right">Expected</th>
                      <th className="py-2 px-3 font-medium text-right">90% Low</th>
                      <th className="py-2 px-3 font-medium text-right">90% High</th>
                      <th className="py-2 px-3 font-medium text-right">P(up)</th>
                      <th className="py-2 pl-3 font-medium text-right">Dir. accuracy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(({ sector, etf, f }) => {
                      const dirAcc = f.validation?.gbm_dir ?? f.validation?.clf_dir;
                      return (
                        <tr key={sector} className="border-b border-border/50 last:border-0">
                          <td className="py-2 pr-3">{SECTOR_LABELS[sector] || sector} <span className="text-muted-foreground text-xs">({etf})</span></td>
                          <td className={`py-2 px-3 text-right tabular-nums font-medium ${f.expected_return_pct >= 0 ? "text-success" : "text-destructive"}`}>
                            {f.expected_return_pct >= 0 ? "+" : ""}{f.expected_return_pct.toFixed(2)}%
                          </td>
                          <td className="py-2 px-3 text-right tabular-nums text-muted-foreground">{f.ci_lower_pct.toFixed(2)}%</td>
                          <td className="py-2 px-3 text-right tabular-nums text-muted-foreground">{f.ci_upper_pct.toFixed(2)}%</td>
                          <td className="py-2 px-3 text-right tabular-nums">{f.prob_up != null ? `${Math.round(f.prob_up * 100)}%` : "—"}</td>
                          <td className="py-2 pl-3 text-right tabular-nums text-muted-foreground">{dirAcc != null ? `${(dirAcc * 100).toFixed(1)}%` : "—"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <p className="text-xs text-muted-foreground mt-4 flex items-start gap-1.5">
              <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              Forecasts come from an ensemble of gradient boosting, ARIMA, and LSTM models with
              EGARCH volatility bands, weighted by out-of-sample walk-forward error. Direction
              accuracy is measured on unseen data — anything meaningfully above 50% is signal.
              This is a research tool, not investment advice.
            </p>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default Predictions;
