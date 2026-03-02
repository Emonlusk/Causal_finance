import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Plus,
  Minus,
  ArrowUpRight,
  ArrowDownRight,
  DollarSign,
  RefreshCw,
  Loader2,
  Search,
  Newspaper,
  Clock,
  ExternalLink,
  Flame,
  Brain,
  Activity,
  BarChart3,
  Zap,
  Target,
  AlertTriangle,
  Info,
  LineChart,
} from "lucide-react";
import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import {
  usePaperTradingBalance,
  useDepositPaperMoney,
  useWithdrawPaperMoney,
  usePortfolios,
  usePortfolioHoldings,
  useExecuteTrade,
  useAllocateCash,
  useCreatePortfolio,
  useStockSearch,
  useNews,
  useTrendingStocks,
  useQuote,
  useCurrentRegime,
  useRegimeRecommendations,
  usePredictSector,
  usePredictVolatility,
  useMLSensitivityMatrix,
} from "@/lib/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";

// Stock to sector mapping for predictions
const STOCK_SECTOR_MAP: Record<string, string> = {
  AAPL: "Technology", MSFT: "Technology", GOOGL: "Technology", AMZN: "Technology", 
  META: "Technology", NVDA: "Technology", AMD: "Technology", INTC: "Technology",
  JPM: "Financials", BAC: "Financials", GS: "Financials", MS: "Financials", WFC: "Financials",
  JNJ: "Healthcare", PFE: "Healthcare", UNH: "Healthcare", MRK: "Healthcare", ABBV: "Healthcare",
  XOM: "Energy", CVX: "Energy", COP: "Energy", SLB: "Energy",
  PG: "Consumer Staples", KO: "Consumer Staples", PEP: "Consumer Staples", WMT: "Consumer Staples",
  DIS: "Consumer Discretionary", TSLA: "Consumer Discretionary", NKE: "Consumer Discretionary",
  CAT: "Industrials", BA: "Industrials", UPS: "Industrials", HON: "Industrials",
  NEE: "Utilities", DUK: "Utilities", SO: "Utilities",
  AMT: "Real Estate", PLD: "Real Estate", SPG: "Real Estate",
  LIN: "Materials", APD: "Materials", DD: "Materials",
};

// Helper to get sector for a stock
const getSectorForStock = (symbol: string): string => {
  return STOCK_SECTOR_MAP[symbol] || "Technology";
};

const PaperTrading = () => {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [depositAmount, setDepositAmount] = useState("");
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null);
  
  // Track previous prices for animation
  const previousPricesRef = useRef<Record<string, number>>({});
  const [priceChanges, setPriceChanges] = useState<Record<string, 'up' | 'down' | null>>({});
  const [tradeSymbol, setTradeSymbol] = useState("");
  const [tradeShares, setTradeShares] = useState("");
  const [tradeAction, setTradeAction] = useState<"buy" | "sell">("buy");
  const [allocateAmount, setAllocateAmount] = useState("");
  const [newPortfolioName, setNewPortfolioName] = useState("");
  const [depositDialogOpen, setDepositDialogOpen] = useState(false);
  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);
  const [tradeDialogOpen, setTradeDialogOpen] = useState(false);
  const [allocateDialogOpen, setAllocateDialogOpen] = useState(false);
  const [createPortfolioDialogOpen, setCreatePortfolioDialogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStockForTrade, setSelectedStockForTrade] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [isAutoRefresh, setIsAutoRefresh] = useState(true);
  const [selectedPredictionSector, setSelectedPredictionSector] = useState("Technology");

  // Queries with auto-refresh intervals
  const { data: balanceData, isLoading: loadingBalance, refetch: refetchBalance } = usePaperTradingBalance();
  const { data: portfoliosData, isLoading: loadingPortfolios } = usePortfolios();
  const { data: holdingsData, isLoading: loadingHoldings, refetch: refetchHoldings } = usePortfolioHoldings(selectedPortfolio || 0);
  const { data: searchResults, isLoading: searchLoading } = useStockSearch(searchQuery);
  const { data: newsData, isLoading: newsLoading } = useNews();
  const { data: trendingData, isLoading: trendingLoading, refetch: refetchTrending } = useTrendingStocks();
  const { data: quoteData, refetch: refetchQuote } = useQuote(selectedStockForTrade || "");
  
  // ML & Causal Queries
  const { data: regimeData, isLoading: regimeLoading } = useCurrentRegime();
  const { data: recommendationsData, isLoading: recsLoading } = useRegimeRecommendations();
  const { data: sensitivityData, isLoading: sensitivityLoading } = useMLSensitivityMatrix();
  
  // ML Prediction Mutations
  const sectorPrediction = usePredictSector();
  const volatilityPrediction = usePredictVolatility();

  // Auto-refresh mechanism
  const refreshAllPrices = useCallback(() => {
    refetchTrending();
    if (selectedStockForTrade) refetchQuote();
    if (selectedPortfolio) refetchHoldings();
    setLastRefresh(new Date());
  }, [refetchTrending, refetchQuote, refetchHoldings, selectedStockForTrade, selectedPortfolio]);

  // Auto-refresh every 10 seconds when enabled
  useEffect(() => {
    if (!isAutoRefresh || !isAuthenticated) return;
    
    const interval = setInterval(() => {
      refreshAllPrices();
    }, 10000); // 10 seconds

    return () => clearInterval(interval);
  }, [isAutoRefresh, isAuthenticated, refreshAllPrices]);

  // Fetch predictions when sector changes
  useEffect(() => {
    if (selectedPredictionSector && isAuthenticated) {
      sectorPrediction.mutate({ sector: selectedPredictionSector, horizon: 5 });
      volatilityPrediction.mutate({ sector: selectedPredictionSector, horizon: 5 });
    }
  }, [selectedPredictionSector, isAuthenticated]);

  // Mutations
  const depositMutation = useDepositPaperMoney();
  const withdrawMutation = useWithdrawPaperMoney();
  const tradeMutation = useExecuteTrade();
  const allocateMutation = useAllocateCash();
  const createPortfolioMutation = useCreatePortfolio();

  const cashBalance = balanceData?.cash_balance || 0;
  const portfolios = portfoliosData?.portfolios || [];
  const news = newsData?.news || [];
  const trending = trendingData?.trending || [];

  const handleDeposit = async () => {
    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount <= 0) return;
    
    try {
      await depositMutation.mutateAsync(amount);
      setDepositAmount("");
      setDepositDialogOpen(false);
      refetchBalance();
    } catch (error) {
      console.error("Deposit failed:", error);
    }
  };

  const handleWithdraw = async () => {
    const amount = parseFloat(withdrawAmount);
    if (isNaN(amount) || amount <= 0) return;
    
    try {
      await withdrawMutation.mutateAsync(amount);
      setWithdrawAmount("");
      setWithdrawDialogOpen(false);
      refetchBalance();
    } catch (error) {
      console.error("Withdrawal failed:", error);
    }
  };

  const handleTrade = async () => {
    if (!selectedPortfolio || !tradeSymbol || !tradeShares) return;
    const shares = parseFloat(tradeShares);
    if (isNaN(shares) || shares <= 0) return;

    try {
      await tradeMutation.mutateAsync({
        portfolioId: selectedPortfolio,
        data: {
          symbol: tradeSymbol.toUpperCase(),
          action: tradeAction,
          shares,
        },
      });
      setTradeSymbol("");
      setTradeShares("");
      setTradeDialogOpen(false);
      setSelectedStockForTrade(null);
      refetchHoldings();
      refetchBalance();
    } catch (error) {
      console.error("Trade failed:", error);
    }
  };

  const handleAllocate = async () => {
    if (!selectedPortfolio) return;
    const amount = parseFloat(allocateAmount);
    if (isNaN(amount) || amount <= 0) return;

    try {
      await allocateMutation.mutateAsync({
        portfolioId: selectedPortfolio,
        amount,
      });
      setAllocateAmount("");
      setAllocateDialogOpen(false);
      refetchBalance();
      refetchHoldings();
    } catch (error) {
      console.error("Allocation failed:", error);
    }
  };

  const handleCreatePortfolio = async () => {
    if (!newPortfolioName.trim()) return;

    try {
      await createPortfolioMutation.mutateAsync({
        name: newPortfolioName,
        portfolio_type: "paper_trading",
      });
      setNewPortfolioName("");
      setCreatePortfolioDialogOpen(false);
    } catch (error) {
      console.error("Create portfolio failed:", error);
    }
  };

  const openTradeForStock = (symbol: string) => {
    setTradeSymbol(symbol);
    setSelectedStockForTrade(symbol);
    setTradeDialogOpen(true);
  };

  const holdings = holdingsData?.holdings || [];
  const totalValue = holdingsData?.total_value || 0;
  const portfolioCash = holdingsData?.cash_balance || 0;
  const totalEquity = holdingsData?.total_equity || 0;

  // Detect price changes for animation effects
  useEffect(() => {
    if (!holdings || holdings.length === 0) return;
    
    const newChanges: Record<string, 'up' | 'down' | null> = {};
    
    holdings.forEach((holding: { symbol: string; current_price: number }) => {
      const prevPrice = previousPricesRef.current[holding.symbol];
      if (prevPrice !== undefined && prevPrice !== holding.current_price) {
        newChanges[holding.symbol] = holding.current_price > prevPrice ? 'up' : 'down';
      }
      previousPricesRef.current[holding.symbol] = holding.current_price;
    });
    
    if (Object.keys(newChanges).length > 0) {
      setPriceChanges(newChanges);
      // Clear animations after 2 seconds
      setTimeout(() => setPriceChanges({}), 2000);
    }
  }, [holdings]);

  // Calculate estimated trade cost
  const estimatedCost = useMemo(() => {
    if (!quoteData?.quote?.price || !tradeShares) return 0;
    return quoteData.quote.price * parseFloat(tradeShares || "0");
  }, [quoteData, tradeShares]);

  if (!isAuthenticated) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-[60vh]">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle>Sign in Required</CardTitle>
              <CardDescription>
                Please sign in to access paper trading features
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" onClick={() => window.location.href = '/login'}>
                Sign In
              </Button>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              Paper Trading
              {isAutoRefresh && (
                <Badge variant="outline" className="animate-pulse text-green-500 border-green-500/30">
                  <Activity className="w-3 h-3 mr-1" /> LIVE
                </Badge>
              )}
            </h2>
            <p className="text-muted-foreground">
              Practice trading with real-time prices, ML predictions & causal insights
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-xs text-muted-foreground mr-2">
              Last update: {lastRefresh.toLocaleTimeString()}
            </div>
            <Button
              variant={isAutoRefresh ? "default" : "outline"}
              size="sm"
              onClick={() => setIsAutoRefresh(!isAutoRefresh)}
              className={isAutoRefresh ? "bg-green-600 hover:bg-green-700" : ""}
            >
              <Zap className={`w-4 h-4 mr-1 ${isAutoRefresh ? "animate-pulse" : ""}`} />
              {isAutoRefresh ? "Live" : "Paused"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                refreshAllPrices();
                refetchBalance();
                queryClient.invalidateQueries({ queryKey: ['news'] });
              }}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Account Summary Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cash Balance</CardTitle>
              <Wallet className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              {loadingBalance ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  ${cashBalance.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </div>
              )}
              <div className="flex gap-2 mt-3">
                <Dialog open={depositDialogOpen} onOpenChange={setDepositDialogOpen}>
                  <DialogTrigger asChild>
                    <Button size="sm" className="flex-1 bg-blue-600 hover:bg-blue-700">
                      <Plus className="w-3 h-3 mr-1" /> Deposit
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Deposit Virtual Funds</DialogTitle>
                      <DialogDescription>
                        Add virtual money to your paper trading account. This is play money!
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label>Amount ($)</Label>
                        <Input
                          type="number"
                          placeholder="10000"
                          value={depositAmount}
                          onChange={(e) => setDepositAmount(e.target.value)}
                        />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {[1000, 10000, 50000, 100000].map((amt) => (
                          <Button
                            key={amt}
                            variant="outline"
                            size="sm"
                            onClick={() => setDepositAmount(amt.toString())}
                          >
                            ${amt.toLocaleString()}
                          </Button>
                        ))}
                      </div>
                    </div>
                    <DialogFooter>
                      <Button onClick={handleDeposit} disabled={depositMutation.isPending}>
                        {depositMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        Deposit
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>

                <Dialog open={withdrawDialogOpen} onOpenChange={setWithdrawDialogOpen}>
                  <DialogTrigger asChild>
                    <Button size="sm" variant="outline" className="flex-1">
                      <Minus className="w-3 h-3 mr-1" /> Withdraw
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Withdraw Virtual Funds</DialogTitle>
                      <DialogDescription>
                        Remove virtual money from your account
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <div className="space-y-2">
                        <Label>Amount ($)</Label>
                        <Input
                          type="number"
                          placeholder="1000"
                          value={withdrawAmount}
                          onChange={(e) => setWithdrawAmount(e.target.value)}
                        />
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Available: ${cashBalance.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                    <DialogFooter>
                      <Button onClick={handleWithdraw} disabled={withdrawMutation.isPending}>
                        {withdrawMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                        Withdraw
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {selectedPortfolio ? "Holdings value" : "Select portfolio"}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Portfolio Cash</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                ${portfolioCash.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Available for trading
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Equity</CardTitle>
              <DollarSign className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-primary">
                ${totalEquity.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Holdings + Cash
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Main Trading Interface */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column: Portfolios & Stock Search */}
          <div className="space-y-6">
            {/* Portfolio Selection */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center justify-between">
                  <span>Your Portfolios</span>
                  <Dialog open={createPortfolioDialogOpen} onOpenChange={setCreatePortfolioDialogOpen}>
                    <DialogTrigger asChild>
                      <Button size="sm" variant="outline">
                        <Plus className="w-3 h-3 mr-1" /> New
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Create Portfolio</DialogTitle>
                        <DialogDescription>
                          Create a new paper trading portfolio
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4 py-4">
                        <div className="space-y-2">
                          <Label>Portfolio Name</Label>
                          <Input
                            placeholder="My Trading Portfolio"
                            value={newPortfolioName}
                            onChange={(e) => setNewPortfolioName(e.target.value)}
                          />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button onClick={handleCreatePortfolio} disabled={createPortfolioMutation.isPending}>
                          {createPortfolioMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                          Create
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {loadingPortfolios ? (
                  <div className="space-y-2">
                    {[1, 2].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
                  </div>
                ) : portfolios.length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <p className="text-sm">No portfolios yet</p>
                    <p className="text-xs mt-1">Create one to start trading!</p>
                  </div>
                ) : (
                  portfolios.map((portfolio) => (
                    <div
                      key={portfolio.id}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedPortfolio === portfolio.id
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "hover:bg-muted/50 hover:border-muted-foreground/20"
                      }`}
                      onClick={() => setSelectedPortfolio(portfolio.id)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">{portfolio.name}</p>
                          <p className="text-xs text-muted-foreground capitalize">
                            {portfolio.portfolio_type.replace('_', ' ')}
                          </p>
                        </div>
                        {selectedPortfolio === portfolio.id && (
                          <Badge variant="default" className="text-xs">Active</Badge>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            {/* Stock Search */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  Search Stocks
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Input
                  placeholder="Search by symbol (AAPL, MSFT...)"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value.toUpperCase())}
                />
                <ScrollArea className="h-[200px]">
                  {searchLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
                    </div>
                  ) : searchResults?.results?.length ? (
                    <div className="space-y-2">
                      {searchResults.results.map((stock) => (
                        <div
                          key={stock.symbol}
                          className="p-2 rounded border hover:bg-muted/50 cursor-pointer"
                          onClick={() => selectedPortfolio && openTradeForStock(stock.symbol)}
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-medium text-sm">{stock.symbol}</p>
                              <p className="text-xs text-muted-foreground truncate max-w-[150px]">
                                {stock.name}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="font-medium text-sm">${stock.price.toFixed(2)}</p>
                              <p className={`text-xs ${stock.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : searchQuery.length >= 1 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">No results</p>
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      Type a symbol to search
                    </p>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>

            {/* Trending Stocks */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Flame className="w-4 h-4 text-orange-500" />
                  Trending Stocks
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[200px]">
                  {trendingLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {trending.slice(0, 8).map((stock) => (
                        <div
                          key={stock.symbol}
                          className="flex justify-between items-center p-2 rounded hover:bg-muted/50 cursor-pointer"
                          onClick={() => selectedPortfolio && openTradeForStock(stock.symbol)}
                        >
                          <div className="flex items-center gap-2">
                            {stock.change >= 0 ? (
                              <ArrowUpRight className="w-4 h-4 text-green-500" />
                            ) : (
                              <ArrowDownRight className="w-4 h-4 text-red-500" />
                            )}
                            <span className="font-medium text-sm">{stock.symbol}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-sm">${stock.price.toFixed(2)}</span>
                            <span className={`ml-2 text-xs ${stock.change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                              {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>

          {/* Center Column: Holdings */}
          <Card className="lg:col-span-1">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span>Holdings</span>
                {selectedPortfolio && (
                  <div className="flex gap-2">
                    <Dialog open={allocateDialogOpen} onOpenChange={setAllocateDialogOpen}>
                      <DialogTrigger asChild>
                        <Button size="sm" variant="outline">
                          <DollarSign className="w-3 h-3 mr-1" /> Fund
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Allocate Funds</DialogTitle>
                          <DialogDescription>
                            Move cash from your account to this portfolio
                          </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                          <div className="space-y-2">
                            <Label>Amount ($)</Label>
                            <Input
                              type="number"
                              placeholder="5000"
                              value={allocateAmount}
                              onChange={(e) => setAllocateAmount(e.target.value)}
                            />
                          </div>
                          <p className="text-sm text-muted-foreground">
                            Available: ${cashBalance.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                          </p>
                        </div>
                        <DialogFooter>
                          <Button onClick={handleAllocate} disabled={allocateMutation.isPending}>
                            {allocateMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                            Allocate
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>

                    <Dialog open={tradeDialogOpen} onOpenChange={(open) => {
                      setTradeDialogOpen(open);
                      if (!open) setSelectedStockForTrade(null);
                    }}>
                      <DialogTrigger asChild>
                        <Button size="sm">
                          <ArrowUpRight className="w-3 h-3 mr-1" /> Trade
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Execute Trade</DialogTitle>
                          <DialogDescription>
                            Buy or sell stocks at real-time prices
                          </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                              <Label>Action</Label>
                              <Select value={tradeAction} onValueChange={(v) => setTradeAction(v as "buy" | "sell")}>
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="buy">
                                    <span className="flex items-center gap-2">
                                      <ArrowUpRight className="w-3 h-3 text-green-500" /> Buy
                                    </span>
                                  </SelectItem>
                                  <SelectItem value="sell">
                                    <span className="flex items-center gap-2">
                                      <ArrowDownRight className="w-3 h-3 text-red-500" /> Sell
                                    </span>
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-2">
                              <Label>Symbol</Label>
                              <Input
                                placeholder="AAPL"
                                value={tradeSymbol}
                                onChange={(e) => {
                                  const symbol = e.target.value.toUpperCase();
                                  setTradeSymbol(symbol);
                                  setSelectedStockForTrade(symbol);
                                }}
                              />
                            </div>
                          </div>
                          <div className="space-y-2">
                            <Label>Shares</Label>
                            <Input
                              type="number"
                              placeholder="10"
                              value={tradeShares}
                              onChange={(e) => setTradeShares(e.target.value)}
                            />
                          </div>
                          
                          {quoteData?.quote && (
                            <div className="p-3 rounded-lg bg-muted/50 space-y-2">
                              <div className="flex justify-between text-sm">
                                <span className="text-muted-foreground">Current Price:</span>
                                <span className="font-medium">${quoteData.quote.price.toFixed(2)}</span>
                              </div>
                              {tradeShares && (
                                <div className="flex justify-between text-sm">
                                  <span className="text-muted-foreground">Estimated Total:</span>
                                  <span className="font-bold text-primary">${estimatedCost.toFixed(2)}</span>
                                </div>
                              )}
                            </div>
                          )}
                          
                          <p className="text-xs text-muted-foreground">
                            Portfolio cash: ${portfolioCash.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                          </p>
                        </div>
                        <DialogFooter>
                          <Button
                            onClick={handleTrade}
                            disabled={tradeMutation.isPending || !tradeSymbol || !tradeShares}
                            className={tradeAction === 'buy' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
                          >
                            {tradeMutation.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                            {tradeAction === "buy" ? "Buy" : "Sell"} {tradeSymbol}
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  </div>
                )}
              </CardTitle>
              <CardDescription>
                {selectedPortfolio ? `${holdings.length} positions` : "Select a portfolio"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!selectedPortfolio ? (
                <div className="text-center py-12 text-muted-foreground">
                  <p className="text-sm">Select a portfolio to view holdings</p>
                </div>
              ) : loadingHoldings ? (
                <div className="space-y-2">
                  {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
                </div>
              ) : holdings.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <p className="text-sm">No holdings yet</p>
                  <p className="text-xs mt-1">Fund portfolio and start trading!</p>
                </div>
              ) : (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-2">
                    {holdings.map((holding) => {
                      const priceChange = priceChanges[holding.symbol];
                      const isUp = priceChange === 'up';
                      const isDown = priceChange === 'down';
                      
                      return (
                      <div 
                        key={holding.symbol} 
                        className={`p-3 rounded-lg border transition-all duration-500 ${
                          isUp ? 'bg-green-500/10 border-green-500/50' : 
                          isDown ? 'bg-red-500/10 border-red-500/50' : ''
                        }`}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-bold">{holding.symbol}</p>
                              {priceChange && (
                                <span className={`text-xs px-1.5 py-0.5 rounded animate-pulse ${
                                  isUp ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
                                }`}>
                                  {isUp ? '▲' : '▼'}
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {holding.shares} shares @ ${holding.avg_cost.toFixed(2)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className={`font-medium transition-colors duration-300 ${
                              isUp ? 'text-green-500' : isDown ? 'text-red-500' : ''
                            }`}>
                              ${holding.market_value.toFixed(2)}
                            </p>
                            <div className={`text-xs flex items-center justify-end gap-1 ${
                              holding.gain_loss >= 0 ? 'text-green-500' : 'text-red-500'
                            }`}>
                              {holding.gain_loss >= 0 ? (
                                <ArrowUpRight className="w-3 h-3" />
                              ) : (
                                <ArrowDownRight className="w-3 h-3" />
                              )}
                              {holding.gain_loss >= 0 ? '+' : ''}${holding.gain_loss.toFixed(2)} ({holding.gain_loss_pct.toFixed(2)}%)
                            </div>
                          </div>
                        </div>
                        <div className="flex justify-between items-center text-xs">
                          <div className="flex items-center gap-3">
                            <span className={`font-mono font-medium ${
                              isUp ? 'text-green-500' : isDown ? 'text-red-500' : 'text-foreground'
                            }`}>
                              ${holding.current_price.toFixed(2)}
                            </span>
                            {holding.day_change !== undefined && (
                              <span className={`flex items-center gap-0.5 ${
                                holding.day_change >= 0 ? 'text-green-500' : 'text-red-500'
                              }`}>
                                {holding.day_change >= 0 ? (
                                  <TrendingUp className="w-3 h-3" />
                                ) : (
                                  <TrendingDown className="w-3 h-3" />
                                )}
                                {holding.day_change >= 0 ? '+' : ''}{holding.day_change_pct?.toFixed(2)}%
                              </span>
                            )}
                            {priceChange && (
                              <span className={`animate-pulse px-1 py-0.5 rounded text-[10px] font-bold ${
                                isUp ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
                              }`}>
                                LIVE
                              </span>
                            )}
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 text-xs"
                            onClick={() => openTradeForStock(holding.symbol)}
                          >
                            Trade
                          </Button>
                        </div>
                      </div>
                    );})}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>

          {/* Right Column: News */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Newspaper className="w-4 h-4" />
                Market News
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                {newsLoading ? (
                  <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="space-y-2">
                        <Skeleton className="h-4 w-full" />
                        <Skeleton className="h-3 w-3/4" />
                      </div>
                    ))}
                  </div>
                ) : news.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No news available
                  </p>
                ) : (
                  <div className="space-y-4">
                    {news.map((item, idx) => {
                      // Only render as link if we have a valid URL
                      const hasValidLink = item.link && item.link.startsWith('http');
                      const Wrapper = hasValidLink ? 'a' : 'div';
                      const wrapperProps = hasValidLink ? {
                        href: item.link,
                        target: "_blank",
                        rel: "noopener noreferrer",
                      } : {};
                      
                      return (
                        <Wrapper
                          key={idx}
                          {...wrapperProps}
                          className={`block p-3 rounded-lg border transition-colors ${hasValidLink ? 'hover:bg-muted/50 cursor-pointer' : 'opacity-80'}`}
                        >
                          <div className="flex gap-3">
                            {item.thumbnail && (
                              <img
                                src={item.thumbnail}
                                alt=""
                                className="w-16 h-16 object-cover rounded"
                              />
                            )}
                            <div className="flex-1 min-w-0">
                              <p className={`font-medium text-sm line-clamp-2 ${hasValidLink ? 'hover:text-primary' : ''}`}>
                                {item.title}
                              </p>
                              <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                                <span>{item.publisher}</span>
                                {item.published && (
                                  <>
                                    <span>•</span>
                                    <Clock className="w-3 h-3" />
                                    <span>
                                      {new Date(item.published).toLocaleDateString()}
                                    </span>
                                  </>
                                )}
                              </div>
                              {item.related_tickers?.length > 0 && (
                                <div className="flex gap-1 mt-2 flex-wrap">
                                  {item.related_tickers.slice(0, 3).map((ticker) => (
                                    <Badge key={ticker} variant="secondary" className="text-xs">
                                      {ticker}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                            {hasValidLink && (
                              <ExternalLink className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
                            )}
                          </div>
                        </Wrapper>
                      );
                    })}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* ML Predictions & Causal Insights Section */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Left: ML Predictions */}
          <Card className="bg-gradient-to-br from-purple-500/5 to-indigo-500/5 border-purple-500/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Brain className="w-4 h-4 text-purple-500" />
                ML Stock Predictions
                <Badge variant="outline" className="ml-auto text-purple-500 border-purple-500/30">
                  AI-Powered
                </Badge>
              </CardTitle>
              <CardDescription>
                Machine learning forecasts for sector returns and volatility
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Sector Selector */}
              <div className="flex gap-2 items-center">
                <Label className="text-sm">Analyze Sector:</Label>
                <Select value={selectedPredictionSector} onValueChange={setSelectedPredictionSector}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {["Technology", "Financials", "Healthcare", "Energy", "Consumer Staples", 
                      "Consumer Discretionary", "Industrials", "Utilities", "Real Estate", "Materials"
                    ].map((sector) => (
                      <SelectItem key={sector} value={sector}>{sector}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button 
                  size="sm" 
                  variant="ghost"
                  onClick={() => {
                    sectorPrediction.mutate({ sector: selectedPredictionSector, horizon: 5 });
                    volatilityPrediction.mutate({ sector: selectedPredictionSector, horizon: 5 });
                  }}
                >
                  <RefreshCw className={`w-3 h-3 ${sectorPrediction.isPending ? 'animate-spin' : ''}`} />
                </Button>
              </div>

              {/* Return Prediction */}
              <div className="p-4 rounded-lg bg-background/50 border">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <LineChart className="w-4 h-4 text-blue-500" />
                    <span className="font-medium text-sm">5-Day Return Forecast</span>
                  </div>
                  {sectorPrediction.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                </div>
                {sectorPrediction.data?.predictions ? (
                  <div className="space-y-2">
                    {(Array.isArray(sectorPrediction.data.predictions)
                      ? sectorPrediction.data.predictions
                      : sectorPrediction.data.predictions.mean || []
                    ).slice(0, 5).map((pred: number, idx: number) => {
                      const isPositive = pred >= 0;
                      return (
                        <div key={idx} className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground w-12">Day {idx + 1}</span>
                          <div className="flex-1">
                            <Progress 
                              value={Math.min(Math.abs(pred) * 100, 100)} 
                              className={`h-2 ${isPositive ? '[&>div]:bg-green-500' : '[&>div]:bg-red-500'}`}
                            />
                          </div>
                          <span className={`text-sm font-medium w-16 text-right ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
                            {isPositive ? '+' : ''}{(pred * 100).toFixed(2)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : sectorPrediction.isError ? (
                  <div className="flex items-center gap-2 text-amber-500 text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    <span>ML models not yet trained. Train models to see predictions.</span>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Select a sector and click refresh</p>
                )}
              </div>

              {/* Volatility Prediction */}
              <div className="p-4 rounded-lg bg-background/50 border">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-orange-500" />
                    <span className="font-medium text-sm">Volatility Forecast</span>
                  </div>
                  {volatilityPrediction.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                </div>
                {(volatilityPrediction.data?.volatility || volatilityPrediction.data?.predictions?.volatility) ? (
                  <div className="space-y-2">
                    {(volatilityPrediction.data.volatility || volatilityPrediction.data.predictions?.volatility || []).slice(0, 5).map((vol: number, idx: number) => {
                      const riskLevel = vol > 0.03 ? 'High' : vol > 0.015 ? 'Medium' : 'Low';
                      const riskColor = vol > 0.03 ? 'text-red-500' : vol > 0.015 ? 'text-amber-500' : 'text-green-500';
                      return (
                        <div key={idx} className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground w-12">Day {idx + 1}</span>
                          <div className="flex-1">
                            <Progress 
                              value={Math.min(vol * 2000, 100)} 
                              className="h-2 [&>div]:bg-orange-500"
                            />
                          </div>
                          <Badge variant="outline" className={`text-xs ${riskColor}`}>
                            {riskLevel}
                          </Badge>
                          <span className="text-sm font-medium w-14 text-right">
                            {(vol * 100).toFixed(2)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : volatilityPrediction.isError ? (
                  <div className="flex items-center gap-2 text-amber-500 text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    <span>ML models not yet trained</span>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Volatility prediction will appear here</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Right: Market Regime & Causal Insights */}
          <Card className="bg-gradient-to-br from-cyan-500/5 to-blue-500/5 border-cyan-500/20">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Target className="w-4 h-4 text-cyan-500" />
                Market Regime & Causal Insights
                <Badge variant="outline" className="ml-auto text-cyan-500 border-cyan-500/30">
                  Causal AI
                </Badge>
              </CardTitle>
              <CardDescription>
                Understand current market conditions and causal relationships
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="regime" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="regime">Regime</TabsTrigger>
                  <TabsTrigger value="recommendations">Actions</TabsTrigger>
                  <TabsTrigger value="sensitivity">Causality</TabsTrigger>
                </TabsList>
                
                <TabsContent value="regime" className="mt-4 space-y-4">
                  {regimeLoading ? (
                    <div className="space-y-2">
                      <Skeleton className="h-16 w-full" />
                      <Skeleton className="h-24 w-full" />
                    </div>
                  ) : (() => {
                    // Extract regime - handle both nested and flat structure
                    const regimeInfo = regimeData?.regime;
                    const currentRegime = typeof regimeInfo === 'object' 
                      ? regimeInfo?.current_regime 
                      : regimeInfo;
                    const regimeMessage = typeof regimeInfo === 'object' 
                      ? regimeInfo?.message 
                      : null;
                    const confidence = regimeData?.confidence;
                    
                    // Format regime name for display
                    const formatRegime = (r: string) => {
                      if (!r) return 'Unknown';
                      // Convert snake_case or simple strings to Title Case
                      return r.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
                    };
                    
                    const displayRegime = formatRegime(currentRegime || 'sideways');
                    
                    return currentRegime || regimeMessage ? (
                    <>
                      <div className="p-4 rounded-lg bg-background/50 border">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm text-muted-foreground">Current Market Regime</span>
                          <Badge 
                            variant="default"
                            className={
                              currentRegime?.toLowerCase().includes('bull') ? 'bg-green-500' :
                              currentRegime?.toLowerCase().includes('bear') ? 'bg-red-500' :
                              currentRegime?.toLowerCase().includes('high') || currentRegime?.toLowerCase().includes('volatile') ? 'bg-orange-500' :
                              'bg-blue-500'
                            }
                          >
                            {displayRegime}
                          </Badge>
                        </div>
                        <p className="text-2xl font-bold">
                          {displayRegime}
                        </p>
                        <p className="text-sm text-muted-foreground mt-2">
                          {regimeMessage || getRegimeDescription(displayRegime)}
                        </p>
                      </div>
                      
                      {confidence && (
                        <div className="p-3 rounded-lg bg-background/50 border">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-muted-foreground">Model Confidence</span>
                            <span className="font-medium">{(confidence * 100).toFixed(1)}%</span>
                          </div>
                          <Progress value={confidence * 100} className="mt-2 h-2" />
                        </div>
                      )}
                    </>
                    ) : (
                    <div className="text-center py-8">
                      <Info className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">
                        Train ML models to detect market regimes
                      </p>
                    </div>
                  );
                  })()}
                </TabsContent>

                <TabsContent value="recommendations" className="mt-4">
                  {recsLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
                    </div>
                  ) : recommendationsData?.recommendations ? (
                    <div className="space-y-2">
                      {recommendationsData.recommendations.map((rec: any, idx: number) => (
                        <div key={idx} className="p-3 rounded-lg border bg-background/50">
                          <div className="flex items-start gap-3">
                            <div className={`p-2 rounded ${
                              rec.action === 'buy' ? 'bg-green-500/10 text-green-500' :
                              rec.action === 'sell' ? 'bg-red-500/10 text-red-500' :
                              'bg-blue-500/10 text-blue-500'
                            }`}>
                              {rec.action === 'buy' ? <TrendingUp className="w-4 h-4" /> :
                               rec.action === 'sell' ? <TrendingDown className="w-4 h-4" /> :
                               <BarChart3 className="w-4 h-4" />}
                            </div>
                            <div className="flex-1">
                              <p className="font-medium text-sm">{rec.sector || rec.asset}</p>
                              <p className="text-xs text-muted-foreground">{rec.reason}</p>
                            </div>
                            <Badge variant="outline" className="text-xs capitalize">
                              {rec.action}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Info className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">
                        No recommendations available. Train ML models first.
                      </p>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="sensitivity" className="mt-4">
                  {sensitivityLoading ? (
                    <Skeleton className="h-48 w-full" />
                  ) : sensitivityData?.matrix ? (
                    <div className="space-y-3">
                      <p className="text-sm text-muted-foreground">
                        How macroeconomic factors causally impact sectors:
                      </p>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(sensitivityData.matrix).slice(0, 6).map(([factor, impacts]: [string, any]) => (
                          <div key={factor} className="p-2 rounded border bg-background/50">
                            <p className="text-xs font-medium truncate">{factor}</p>
                            {typeof impacts === 'object' && (
                              <div className="flex items-center gap-1 mt-1">
                                <span className="text-xs text-muted-foreground">Impact:</span>
                                <span className={`text-xs font-medium ${
                                  Object.values(impacts)[0] as number > 0 ? 'text-green-500' : 'text-red-500'
                                }`}>
                                  {((Object.values(impacts)[0] as number) * 100).toFixed(1)}%
                                </span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Info className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm text-muted-foreground">
                        Causal sensitivity matrix not available
                      </p>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};

// Helper function for regime descriptions
const getRegimeDescription = (regime: string): string => {
  const descriptions: Record<string, string> = {
    'Bull Market': 'Markets are trending upward with positive sentiment. Consider growth-oriented positions.',
    'Bear Market': 'Markets are trending downward. Consider defensive positions or hedging strategies.',
    'High Volatility': 'Expect large price swings. Reduce position sizes and consider volatility strategies.',
    'Low Volatility': 'Markets are calm. Good environment for steady accumulation.',
    'Recovery': 'Markets recovering from downturn. Early cycle opportunities may exist.',
    'Recession': 'Economic contraction phase. Focus on capital preservation.',
  };
  return descriptions[regime] || 'Market conditions are evolving. Monitor closely.';
};

export default PaperTrading;
