import { TrendingUp, TrendingDown, Activity, Lightbulb, ArrowUpRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function SummaryCards() {
  return (
    <div className="grid md:grid-cols-3 gap-6">
      {/* Portfolio Performance */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Your Portfolio
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-bold">$125,430</span>
            <span className="flex items-center text-sm font-medium text-success">
              <TrendingUp className="w-4 h-4 mr-1" />
              +8.3%
            </span>
          </div>
          <div className="mt-4 h-12">
            {/* Mini Sparkline */}
            <svg viewBox="0 0 100 30" className="w-full h-full">
              <path
                d="M0,25 L10,22 L20,24 L30,18 L40,20 L50,15 L60,12 L70,14 L80,8 L90,10 L100,5"
                fill="none"
                stroke="hsl(var(--success))"
                strokeWidth="2"
              />
              <path
                d="M0,25 L10,22 L20,24 L30,18 L40,20 L50,15 L60,12 L70,14 L80,8 L90,10 L100,5 L100,30 L0,30 Z"
                fill="hsl(var(--success))"
                fillOpacity="0.1"
              />
            </svg>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            vs S&P 500: <span className="text-foreground font-medium">+6.1%</span>
          </div>
        </CardContent>
      </Card>

      {/* Market Conditions */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Market State
            </CardTitle>
            <span className="px-2 py-1 bg-warning/10 text-warning text-xs font-medium rounded-full">
              Neutral
            </span>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">VIX</span>
              <div className="flex items-center gap-2">
                <span className="font-semibold">18.2</span>
                <span className="text-xs px-1.5 py-0.5 bg-success/10 text-success rounded">Low</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Fed Rate</span>
              <div className="flex items-center gap-2">
                <span className="font-semibold">4.5%</span>
                <TrendingUp className="w-3 h-3 text-warning" />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">CPI</span>
              <div className="flex items-center gap-2">
                <span className="font-semibold">3.2%</span>
                <TrendingDown className="w-3 h-3 text-success" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Causal Insight */}
      <Card className="bg-primary/5 border-primary/20">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-primary" />
            <CardTitle className="text-sm font-medium text-primary">
              Top Causal Insight
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-foreground font-medium mb-2">
            Tech sector shows -0.8% sensitivity to rate hikes
          </p>
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center gap-1">
              <Activity className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Confidence:</span>
              <span className="font-semibold text-success">92%</span>
            </div>
          </div>
          <Button variant="outline" size="sm" className="w-full border-primary/30 text-primary hover:bg-primary/10">
            Explore Analysis
            <ArrowUpRight className="w-4 h-4 ml-2" />
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
