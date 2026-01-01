import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
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
} from "lucide-react";
import { useState, useMemo } from "react";
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
} from "@/lib/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";

const PaperTrading = () => {
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();
  const [depositAmount, setDepositAmount] = useState("");
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null);
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

  // Queries
  const { data: balanceData, isLoading: loadingBalance, refetch: refetchBalance } = usePaperTradingBalance();
  const { data: portfoliosData, isLoading: loadingPortfolios } = usePortfolios();
  const { data: holdingsData, isLoading: loadingHoldings, refetch: refetchHoldings } = usePortfolioHoldings(selectedPortfolio || 0);
  const { data: searchResults, isLoading: searchLoading } = useStockSearch(searchQuery);
  const { data: newsData, isLoading: newsLoading } = useNews();
  const { data: trendingData, isLoading: trendingLoading } = useTrendingStocks();
  const { data: quoteData } = useQuote(selectedStockForTrade || "");

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
            <h2 className="text-2xl font-bold">Paper Trading</h2>
            <p className="text-muted-foreground">
              Practice trading with real-time prices, zero risk
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              refetchBalance();
              queryClient.invalidateQueries({ queryKey: ['trendingStocks'] });
              queryClient.invalidateQueries({ queryKey: ['news'] });
            }}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
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
                    {holdings.map((holding) => (
                      <div key={holding.symbol} className="p-3 rounded-lg border">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <p className="font-bold">{holding.symbol}</p>
                            <p className="text-xs text-muted-foreground">
                              {holding.shares} shares @ ${holding.avg_cost.toFixed(2)}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-medium">${holding.market_value.toFixed(2)}</p>
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
                        <div className="flex justify-between text-xs text-muted-foreground">
                          <span>Current: ${holding.current_price.toFixed(2)}</span>
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
                    ))}
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
                    {news.map((item, idx) => (
                      <a
                        key={idx}
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block p-3 rounded-lg border hover:bg-muted/50 transition-colors"
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
                            <p className="font-medium text-sm line-clamp-2 hover:text-primary">
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
                          <ExternalLink className="w-4 h-4 flex-shrink-0 text-muted-foreground" />
                        </div>
                      </a>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default PaperTrading;
