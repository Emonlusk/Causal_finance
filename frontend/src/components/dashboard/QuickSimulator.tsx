import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

export function QuickSimulator() {
  const [rateChange, setRateChange] = useState(1);
  const impact = (-4.2 * rateChange).toFixed(1);

  const sectors = [
    { name: "Tech", impact: -0.8 * rateChange },
    { name: "Health", impact: -0.2 * rateChange },
    { name: "Energy", impact: 0.3 * rateChange },
    { name: "Finance", impact: -0.6 * rateChange },
  ];

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
            <div className={`text-2xl font-bold ${parseFloat(impact) < 0 ? "text-destructive" : "text-success"}`}>
              {impact}% projected
            </div>
          </div>

          {/* Mini sector bars */}
          <div className="space-y-2">
            {sectors.map((sector) => (
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
            ))}
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
