import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { usePortfolioTrades } from "@/lib/hooks";
import { History } from "lucide-react";

export function TradeHistoryCard({ portfolioId }: { portfolioId: number }) {
  const { data, isLoading } = usePortfolioTrades(portfolioId);
  const trades = data?.trades || [];
  const realized = data?.realized_pnl_total ?? 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <History className="w-4 h-4 text-primary" /> Order History
            </CardTitle>
            <CardDescription>Every fill with realized P&L on sells</CardDescription>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Realized P&L</div>
            <div className={`text-sm font-semibold tabular-nums ${realized >= 0 ? "text-success" : "text-destructive"}`}>
              {realized >= 0 ? "+" : ""}${Math.abs(realized).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
          </div>
        ) : trades.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            No trades yet — place your first order above.
          </div>
        ) : (
          <ScrollArea className="h-64">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-card">
                <tr className="text-left text-[11px] uppercase tracking-wide text-muted-foreground border-b border-border">
                  <th className="py-2 pr-2 font-medium">Time</th>
                  <th className="py-2 px-2 font-medium">Side</th>
                  <th className="py-2 px-2 font-medium">Symbol</th>
                  <th className="py-2 px-2 font-medium text-right">Shares</th>
                  <th className="py-2 px-2 font-medium text-right">Price</th>
                  <th className="py-2 px-2 font-medium text-right">Total</th>
                  <th className="py-2 pl-2 font-medium text-right">P&L</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr key={t.id} className="border-b border-border/40 last:border-0">
                    <td className="py-1.5 pr-2 text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(t.created_at + "Z").toLocaleString(undefined, {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                      })}
                    </td>
                    <td className="py-1.5 px-2">
                      <Badge
                        variant="outline"
                        className={t.side === "buy"
                          ? "text-success border-success/40 text-[10px] px-1.5"
                          : "text-destructive border-destructive/40 text-[10px] px-1.5"}
                      >
                        {t.side.toUpperCase()}
                      </Badge>
                    </td>
                    <td className="py-1.5 px-2 font-medium">{t.symbol}</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">{t.shares}</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">${t.price.toFixed(2)}</td>
                    <td className="py-1.5 px-2 text-right tabular-nums">${t.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td className={`py-1.5 pl-2 text-right tabular-nums ${
                      t.realized_pnl == null ? "text-muted-foreground"
                        : t.realized_pnl >= 0 ? "text-success" : "text-destructive"
                    }`}>
                      {t.realized_pnl == null ? "—" : `${t.realized_pnl >= 0 ? "+" : ""}$${Math.abs(t.realized_pnl).toFixed(2)}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
