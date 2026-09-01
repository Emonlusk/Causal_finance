import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useBenchmarkPerformance, usePortfolios, usePortfolioPerformance } from "@/lib/hooks";
import { Info, TrendingUp } from "lucide-react";

const timeframes = ["1M", "3M", "1Y", "All"];

export function PerformanceChart() {
  const [selectedTimeframe, setSelectedTimeframe] = useState("1Y");
  
  // Fetch benchmark (S&P 500) data
  const { data: benchmarkData, isLoading: loadingBenchmark } = useBenchmarkPerformance(selectedTimeframe);
  
  // Fetch user's first portfolio for comparison
  const { data: portfoliosData, isLoading: loadingPortfolios } = usePortfolios();
  const firstPortfolioId = portfoliosData?.portfolios?.[0]?.id;
  
  const { data: portfolioPerf, isLoading: loadingPortfolio } = usePortfolioPerformance(
    firstPortfolioId || 0,
    selectedTimeframe
  );

  const isLoading = loadingBenchmark || loadingPortfolios || loadingPortfolio;
  
  // Check if we're using simulated/fallback data
  const isUsingFallbackData = !benchmarkData?.data?.time_series?.length;

  // Transform API data into chart format
  const chartData = useMemo(() => {
    const benchmarkTimeSeries = benchmarkData?.data?.time_series || [];
    const portfolioTimeSeries = portfolioPerf?.performance?.time_series || [];

    if (benchmarkTimeSeries.length === 0) {
      // No real benchmark data at all - don't fabricate a series. The empty
      // state below tells the user there isn't enough data yet instead.
      return [];
    }

    // Merge benchmark and portfolio data. Both are indexed to start at 100
    // so they're comparable on the same scale: the benchmark from its raw
    // close price, the portfolio from its already-cumulative % return.
    const benchmarkBase = benchmarkTimeSeries[0]?.close || 1;

    // Carry the last known portfolio value forward for dates where the
    // portfolio has no matching data point, instead of fabricating motion.
    // Starts at the same 100 baseline as the benchmark until real data
    // arrives.
    let lastKnownPortfolioValue = 100;

    return benchmarkTimeSeries.map((point, index) => {
      const date = new Date(point.date);
      const month = date.toLocaleString("default", { month: "short" });

      const sp500Value = (point.close / benchmarkBase) * 100;
      const portfolioPoint = portfolioTimeSeries[index];
      const portfolioValue = portfolioPoint
        ? 100 + portfolioPoint.return
        : lastKnownPortfolioValue;
      lastKnownPortfolioValue = portfolioValue;

      return {
        month,
        portfolio: Math.round(portfolioValue * 10) / 10,
        sp500: Math.round(sp500Value * 10) / 10,
      };
    });
  }, [benchmarkData, portfolioPerf, selectedTimeframe]);
  
  // Calculate summary stats
  const summaryStats = useMemo(() => {
    if (chartData.length < 2) return null;
    const first = chartData[0];
    const last = chartData[chartData.length - 1];
    return {
      portfolioReturn: ((last.portfolio - first.portfolio) / first.portfolio * 100).toFixed(1),
      sp500Return: ((last.sp500 - first.sp500) / first.sp500 * 100).toFixed(1),
    };
  }, [chartData]);

  return (
    <Card className="col-span-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Performance Comparison</CardTitle>
          <CardDescription className="flex items-center gap-2 mt-1">
            {isUsingFallbackData ? (
              <>
                <Info className="w-3 h-3" />
                Not enough market data yet
              </>
            ) : (
              <>
                <TrendingUp className="w-3 h-3 text-success" />
                Live market data
              </>
            )}
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          {/* Summary Stats */}
          {summaryStats && !isLoading && (
            <div className="hidden md:flex items-center gap-4 mr-4 text-sm">
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Portfolio:</span>
                <span className={parseFloat(summaryStats.portfolioReturn) >= 0 ? 'text-success' : 'text-destructive'}>
                  {parseFloat(summaryStats.portfolioReturn) >= 0 ? '+' : ''}{summaryStats.portfolioReturn}%
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">S&P 500:</span>
                <span className={parseFloat(summaryStats.sp500Return) >= 0 ? 'text-success' : 'text-destructive'}>
                  {parseFloat(summaryStats.sp500Return) >= 0 ? '+' : ''}{summaryStats.sp500Return}%
                </span>
              </div>
            </div>
          )}
          {timeframes.map((tf) => (
            <Button
              key={tf}
              variant={selectedTimeframe === tf ? "default" : "ghost"}
              size="sm"
              onClick={() => setSelectedTimeframe(tf)}
              className={selectedTimeframe === tf ? "" : "text-muted-foreground"}
            >
              {tf}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          {isLoading ? (
            <div className="flex flex-col gap-4 h-full justify-center">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-48 w-full" />
              <Skeleton className="h-4 w-1/2 mx-auto" />
            </div>
          ) : chartData.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 text-center">
              <Info className="w-6 h-6 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Not enough market data yet to show a performance comparison.
              </p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis 
                  dataKey="month" 
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                />
                <YAxis 
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                  }}
                  labelStyle={{ color: "hsl(var(--foreground))" }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="portfolio"
                  name="Your Portfolio"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="sp500"
                  name="S&P 500"
                  stroke="hsl(var(--muted-foreground))"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
