import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Check, 
  AlertTriangle, 
  ArrowRight, 
  Download, 
  Info,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { useState } from "react";

const sectors = [
  { name: "Technology", traditional: 25, causal: 15, color: "bg-primary" },
  { name: "Healthcare", traditional: 20, causal: 25, color: "bg-success" },
  { name: "Energy", traditional: 15, causal: 30, color: "bg-warning" },
  { name: "Financials", traditional: 40, causal: 30, color: "bg-accent" },
];

const traditionalMetrics = {
  expectedReturn: 9.2,
  volatility: 18.4,
  sharpeRatio: 1.2,
  maxDrawdown: -25.3,
};

const causalMetrics = {
  expectedReturn: 10.1,
  volatility: 14.2,
  sharpeRatio: 1.8,
  maxDrawdown: -18.4,
};

const regimeAnalysis = [
  { regime: "Rate Hike", traditional: -8.2, causal: -3.5, improvement: 4.7 },
  { regime: "Inflation Spike", traditional: -5.1, causal: 1.8, improvement: 6.9 },
  { regime: "Recession", traditional: -12.3, causal: -7.9, improvement: 4.4 },
  { regime: "Bull Market", traditional: 15.4, causal: 16.2, improvement: 0.8 },
];

const causalReasons = [
  { factor: "Interest Rate Sensitivity", insight: "Tech reduced due to -0.8% rate impact", confidence: 95 },
  { factor: "Inflation Hedge", insight: "Energy increased for inflation protection", confidence: 88 },
  { factor: "Defensive Positioning", insight: "Healthcare added for stability", confidence: 92 },
  { factor: "Financial Cycle", insight: "Financials balanced for rate environment", confidence: 85 },
];

const PortfolioBuilder = () => {
  const [showReasons, setShowReasons] = useState(false);
  const [allocations, setAllocations] = useState(
    sectors.reduce((acc, s) => ({ ...acc, [s.name]: s.traditional }), {} as Record<string, number>)
  );

  const totalAllocation = Object.values(allocations).reduce((a, b) => a + b, 0);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">Portfolio Builder</h2>
            <p className="text-muted-foreground">Compare traditional vs causal optimization</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button>
              Apply Causal Weights
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>

        {/* Comparison Panels */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Traditional Portfolio */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Markowitz Optimization
                <Badge variant="secondary">Traditional</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Allocation Bars */}
              <div className="space-y-4">
                {sectors.map((sector) => (
                  <div key={sector.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{sector.name}</span>
                      <span className="text-sm text-muted-foreground">{allocations[sector.name]}%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-3 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full ${sector.color} rounded-full transition-all duration-300`}
                          style={{ width: `${allocations[sector.name]}%` }}
                        />
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={allocations[sector.name]}
                        onChange={(e) =>
                          setAllocations((prev) => ({
                            ...prev,
                            [sector.name]: parseInt(e.target.value),
                          }))
                        }
                        className="w-20 h-1 accent-primary"
                      />
                    </div>
                  </div>
                ))}
                <div className={`text-sm font-medium ${totalAllocation === 100 ? "text-success" : "text-destructive"}`}>
                  Total: {totalAllocation}%
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-secondary rounded-lg">
                  <div className="text-xs text-muted-foreground">Expected Return</div>
                  <div className="text-xl font-bold">{traditionalMetrics.expectedReturn}%</div>
                </div>
                <div className="p-3 bg-secondary rounded-lg">
                  <div className="text-xs text-muted-foreground">Volatility</div>
                  <div className="text-xl font-bold">{traditionalMetrics.volatility}%</div>
                </div>
                <div className="p-3 bg-secondary rounded-lg">
                  <div className="text-xs text-muted-foreground">Sharpe Ratio</div>
                  <div className="text-xl font-bold">{traditionalMetrics.sharpeRatio}</div>
                </div>
                <div className="p-3 bg-secondary rounded-lg">
                  <div className="text-xs text-muted-foreground">Max Drawdown</div>
                  <div className="text-xl font-bold text-destructive">{traditionalMetrics.maxDrawdown}%</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Causal Optimized */}
          <Card className="border-accent/50 bg-accent/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                Causal AI Optimization
                <Badge className="bg-accent text-accent-foreground">
                  <Check className="w-3 h-3 mr-1" />
                  Recommended
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Allocation Bars */}
              <div className="space-y-4">
                {sectors.map((sector) => (
                  <div key={sector.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{sector.name}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">{sector.causal}%</span>
                        {sector.causal !== sector.traditional && (
                          <span className={`text-xs ${sector.causal > sector.traditional ? "text-success" : "text-warning"}`}>
                            {sector.causal > sector.traditional ? "↑" : "↓"}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="h-3 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full ${sector.color} rounded-full`}
                        style={{ width: `${sector.causal}%` }}
                      />
                    </div>
                  </div>
                ))}
                <div className="text-sm font-medium text-success">Total: 100%</div>
              </div>

              {/* Metrics with improvements */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-background rounded-lg border border-border">
                  <div className="text-xs text-muted-foreground">Expected Return</div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold">{causalMetrics.expectedReturn}%</span>
                    <span className="text-xs text-success">+{(causalMetrics.expectedReturn - traditionalMetrics.expectedReturn).toFixed(1)}%</span>
                  </div>
                </div>
                <div className="p-3 bg-background rounded-lg border border-border">
                  <div className="text-xs text-muted-foreground">Volatility</div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold">{causalMetrics.volatility}%</span>
                    <span className="text-xs text-success">{(causalMetrics.volatility - traditionalMetrics.volatility).toFixed(1)}%</span>
                  </div>
                </div>
                <div className="p-3 bg-background rounded-lg border border-border">
                  <div className="text-xs text-muted-foreground">Sharpe Ratio</div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold">{causalMetrics.sharpeRatio}</span>
                    <span className="text-xs text-success">+{(causalMetrics.sharpeRatio - traditionalMetrics.sharpeRatio).toFixed(1)}</span>
                  </div>
                </div>
                <div className="p-3 bg-background rounded-lg border border-border">
                  <div className="text-xs text-muted-foreground">Max Drawdown</div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold text-success">{causalMetrics.maxDrawdown}%</span>
                    <span className="text-xs text-success">+{(causalMetrics.maxDrawdown - traditionalMetrics.maxDrawdown).toFixed(1)}%</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Causal Factors Panel */}
        <Card>
          <CardHeader>
            <button
              onClick={() => setShowReasons(!showReasons)}
              className="flex items-center justify-between w-full"
            >
              <CardTitle className="flex items-center gap-2">
                <Info className="w-5 h-5 text-primary" />
                Why these weights?
              </CardTitle>
              {showReasons ? (
                <ChevronUp className="w-5 h-5 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-5 h-5 text-muted-foreground" />
              )}
            </button>
          </CardHeader>
          {showReasons && (
            <CardContent>
              <div className="grid md:grid-cols-2 gap-4">
                {causalReasons.map((reason, index) => (
                  <div key={index} className="p-4 bg-secondary/50 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{reason.factor}</span>
                      <Badge variant="outline">{reason.confidence}% conf.</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{reason.insight}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>

        {/* Regime Analysis */}
        <Card>
          <CardHeader>
            <CardTitle>Regime Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-4 font-medium text-muted-foreground">Economic Regime</th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">Traditional</th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">Causal</th>
                    <th className="text-right py-3 px-4 font-medium text-muted-foreground">Improvement</th>
                  </tr>
                </thead>
                <tbody>
                  {regimeAnalysis.map((row) => (
                    <tr key={row.regime} className="border-b border-border/50">
                      <td className="py-3 px-4 font-medium">{row.regime}</td>
                      <td className={`py-3 px-4 text-right ${row.traditional < 0 ? "text-destructive" : "text-success"}`}>
                        {row.traditional > 0 ? "+" : ""}{row.traditional}%
                      </td>
                      <td className={`py-3 px-4 text-right ${row.causal < 0 ? "text-destructive" : "text-success"}`}>
                        {row.causal > 0 ? "+" : ""}{row.causal}%
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="inline-flex items-center gap-1 text-success">
                          <Check className="w-4 h-4" />
                          +{row.improvement}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default PortfolioBuilder;
