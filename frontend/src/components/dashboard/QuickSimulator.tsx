import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useSensitivityMatrix } from "@/lib/hooks";

export function QuickSimulator() {
  const [rateChange, setRateChange] = useState(1);
  const { data: sensitivityData, isLoading } = useSensitivityMatrix();

  // Extract sector sensitivities from the API response
  const sectors = useMemo(() => {
    const matrix = sensitivityData?.sensitivity_matrix?.matrix;
    if (!matrix || !Array.isArray(matrix)) {
      // Fallback defaults
      return [
        { name: "Tech", sensitivity: -0.8 },
        { name: "Health", sensitivity: -0.2 },
        { name: "Energy", sensitivity: 0.3 },
        { name: "Finance", sensitivity: -0.6 },
      ];
    }
    
    // Map the API response to our format
    return matrix.slice(0, 4).map((item: { sector: string; interest_rates: number }) => ({
      name: item.sector?.replace('_', ' ').split(' ')[0] || 'Unknown',
      sensitivity: item.interest_rates || 0,
    }));
  }, [sensitivityData]);

  // Calculate impacts
  const sectorImpacts = sectors.map(s => ({
    name: s.name,
    impact: s.sensitivity * rateChange,
  }));

  // Calculate overall portfolio impact (weighted average)
  const portfolioImpact = sectorImpacts.reduce((sum, s) => sum + s.impact, 0) / sectorImpacts.length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Quick What-If</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">If rates increase by:</span>
              <span className="font-bold text-primary">+{rateChange.toFixed(1)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={rateChange}
              onChange={(e) => setRateChange(parseFloat(e.target.value))}
              className="w-full h-2 bg-muted rounded-full appearance-none cursor-pointer
                [&::-webkit-slider-thumb]:appearance-none
                [&::-webkit-slider-thumb]:w-4
                [&::-webkit-slider-thumb]:h-4
                [&::-webkit-slider-thumb]:rounded-full
                [&::-webkit-slider-thumb]:bg-primary
                [&::-webkit-slider-thumb]:cursor-pointer"
            />
          </div>

          <div className="p-3 bg-secondary rounded-lg">
            <div className="text-sm text-muted-foreground mb-1">Your portfolio:</div>
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className={`text-2xl font-bold ${portfolioImpact < 0 ? "text-destructive" : "text-success"}`}>
                {portfolioImpact > 0 ? '+' : ''}{portfolioImpact.toFixed(1)}% projected
              </div>
            )}
          </div>

          {/* Mini sector bars */}
          <div className="space-y-2">
            {isLoading ? (
              [1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))
            ) : (
              sectorImpacts.map((sector) => (
                <div key={sector.name} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-12">{sector.name}</span>
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        sector.impact < 0 ? "bg-destructive" : "bg-success"
                      }`}
                      style={{
                        width: `${Math.min(Math.abs(sector.impact) * 50, 100)}%`,
                        marginLeft: sector.impact < 0 ? "auto" : 0,
                      }}
                    />
                  </div>
                  <span className={`text-xs font-medium w-12 text-right ${
                    sector.impact < 0 ? "text-destructive" : "text-success"
                  }`}>
                    {sector.impact > 0 ? "+" : ""}{sector.impact.toFixed(1)}%
                  </span>
                </div>
              ))
            )}
          </div>

          <div className="text-xs text-muted-foreground text-center">
            {sensitivityData?.sensitivity_matrix?.is_ml_trained 
              ? "Using ML-trained sensitivity model" 
              : "Using default sensitivity estimates"}
          </div>

          <Button asChild variant="outline" className="w-full">
            <Link to="/simulator">
              Run Full Scenario Analysis
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
