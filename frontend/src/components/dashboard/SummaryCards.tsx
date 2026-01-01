import { TrendingUp, TrendingDown, Activity, Lightbulb, ArrowUpRight, AlertCircle, Wallet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Link } from "react-router-dom";
import { useMarketIndicators, useCurrentRegime, usePortfolios, useSensitivityMatrix, usePaperTradingBalance } from "@/lib/hooks";

export function SummaryCards() {
  const { data: marketData, isLoading: marketLoading, error: marketError } = useMarketIndicators();
  const { data: regimeData, isLoading: regimeLoading } = useCurrentRegime();
  const { data: portfolioData, isLoading: portfolioLoading } = usePortfolios();
  const { data: sensitivityData, isLoading: sensitivityLoading } = useSensitivityMatrix();
  const { data: balanceData, isLoading: balanceLoading } = usePaperTradingBalance();

  // Calculate total portfolio value including cash and holdings
  const totalValue = (portfolioData?.portfolios?.reduce((sum, p) => {
    const cashBalance = p.cash_balance || 0;
    const holdingsValue = Object.values(p.holdings || {}).reduce((h: number, holding: any) => {
      return h + ((holding.shares || 0) * (holding.avg_cost || 0));
    }, 0);
    return sum + cashBalance + holdingsValue;
  }, 0) || 0) + (balanceData?.cash_balance || 0);

  // Get market indicators
  const indicators = marketData?.indicators;
  const vix = indicators?.vix;
  const fedRate = indicators?.fed_rate;
  const cpi = indicators?.cpi;

  // Get regime info
  const regime = regimeData?.regime;
  const regimeLabel = typeof regime === 'string' ? regime : regime?.current_regime || 'neutral';
  const regimeColor = regimeLabel === 'bull' || regimeLabel === 'bullish' ? 'text-success bg-success/10' :
                      regimeLabel === 'bear' || regimeLabel === 'bearish' ? 'text-destructive bg-destructive/10' :
                      regimeLabel === 'crisis' ? 'text-destructive bg-destructive/10' :
                      'text-warning bg-warning/10';

  // Get top sensitivity insight
  const matrix = sensitivityData?.sensitivity_matrix?.matrix?.[0];
  const topSector = matrix?.sector?.replace(/_/g, ' ') || 'Technology';
  const topSensitivity = matrix?.interest_rates || -0.8;
  
  // Check if user has any portfolios
  const hasPortfolios = portfolioData?.portfolios?.length > 0;

  return (
    <div className="grid md:grid-cols-3 gap-6">
      {/* Portfolio Performance */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Your Portfolio
            </CardTitle>
            {totalValue > 0 && (
              <Badge variant="outline" className="text-xs">
                <Wallet className="w-3 h-3 mr-1" />
                Paper Trading
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {portfolioLoading || balanceLoading ? (
            <Skeleton className="h-10 w-32" />
          ) : totalValue > 0 ? (
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold">
                ${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              {hasPortfolios && (
                <span className="flex items-center text-sm font-medium text-success">
                  <TrendingUp className="w-4 h-4 mr-1" />
                  Active
                </span>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-2xl font-bold text-muted-foreground">$0.00</div>
              <p className="text-sm text-muted-foreground">Start paper trading to see your portfolio value</p>
              <Button asChild size="sm" variant="outline">
                <Link to="/paper-trading">
                  Start Trading
                  <ArrowUpRight className="w-3 h-3 ml-1" />
                </Link>
              </Button>
            </div>
          )}
          {totalValue > 0 && (
            <>
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
                {portfolioData?.portfolios?.length || 0} portfolio(s) • ${balanceData?.cash_balance?.toLocaleString() || '0'} cash available
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Market Conditions */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Market State
            </CardTitle>
            {regimeLoading ? (
              <Skeleton className="h-6 w-16" />
            ) : (
              <span className={`px-2 py-1 text-xs font-medium rounded-full capitalize ${regimeColor}`}>
                {regimeLabel}
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {marketLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
              <Skeleton className="h-6 w-full" />
            </div>
          ) : marketError ? (
            <div className="text-sm text-muted-foreground">Unable to load market data</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">VIX</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{vix?.value?.toFixed(1) || '--'}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    (vix?.value || 0) < 20 ? 'bg-success/10 text-success' :
                    (vix?.value || 0) < 30 ? 'bg-warning/10 text-warning' :
                    'bg-destructive/10 text-destructive'
                  }`}>
                    {(vix?.value || 0) < 20 ? 'Low' : (vix?.value || 0) < 30 ? 'Med' : 'High'}
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Fed Rate</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{fedRate?.value?.toFixed(2) || '--'}%</span>
                  {fedRate?.trend === 'up' ? (
                    <TrendingUp className="w-3 h-3 text-warning" />
                  ) : fedRate?.trend === 'down' ? (
                    <TrendingDown className="w-3 h-3 text-success" />
                  ) : null}
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">CPI</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{cpi?.value?.toFixed(1) || '--'}%</span>
                  {(cpi?.change || 0) < 0 ? (
                    <TrendingDown className="w-3 h-3 text-success" />
                  ) : (
                    <TrendingUp className="w-3 h-3 text-warning" />
                  )}
                </div>
              </div>
            </div>
          )}
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
          {sensitivityLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-4 w-3/4" />
            </div>
          ) : (
            <>
              <p className="text-foreground font-medium mb-2">
                {topSector} sector shows {topSensitivity.toFixed(1)}% sensitivity to rate hikes
              </p>
              <div className="flex items-center gap-4 mb-4">
                <div className="flex items-center gap-1">
                  <Activity className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">Source:</span>
                  <span className="font-semibold text-success">
                    {sensitivityData?.sensitivity_matrix?.is_ml_trained ? 'ML Model' : 'Default'}
                  </span>
                </div>
              </div>
            </>
          )}
          <Button asChild variant="outline" size="sm" className="w-full border-primary/30 text-primary hover:bg-primary/10">
            <Link to="/analysis">
              Explore Analysis
              <ArrowUpRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
