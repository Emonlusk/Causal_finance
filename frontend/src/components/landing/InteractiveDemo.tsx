import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowRight, ArrowDown } from "lucide-react";

export function InteractiveDemo() {
  const [rateChange, setRateChange] = useState(0.5);

  // Illustrative sector sensitivities (shaped like the platform's real
  // interest-rate coefficients) showing HOW a causal adjustment propagates
  // from a macro input to sector-level impact - this is a mechanism demo,
  // not a claim about historical or live portfolio performance. Actual
  // backtested performance is reported honestly, with real numbers, in the
  // Verified Results section below - never fabricate a "live" Sharpe ratio
  // or confidence score here.
  const techImpact = (-0.8 * rateChange).toFixed(1);
  const healthImpact = (-0.2 * rateChange).toFixed(1);
  const energyImpact = (0.3 * rateChange).toFixed(1);

  return (
    <section id="demo" className="py-24 bg-muted/40 scroll-mt-20">
      <div className="container mx-auto px-6">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              See Causal AI in Action
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Adjust economic factors and watch how causal relationships 
              propagate through your portfolio in real-time.
            </p>
          </div>
          
          {/* Interactive Demo Card */}
          <div className="bg-card rounded-2xl border border-border shadow-lg overflow-hidden">
            <div className="p-8">
              {/* Slider Control */}
              <div className="mb-8">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-foreground">
                    Interest Rate Change
                  </span>
                  <span className="stat-number text-sm font-bold px-2.5 py-1 rounded-full bg-accent text-accent-foreground">
                    +{rateChange.toFixed(1)}%
                  </span>
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
                    [&::-webkit-slider-thumb]:w-5
                    [&::-webkit-slider-thumb]:h-5
                    [&::-webkit-slider-thumb]:rounded-full
                    [&::-webkit-slider-thumb]:bg-accent
                    [&::-webkit-slider-thumb]:shadow-md
                    [&::-webkit-slider-thumb]:cursor-pointer
                    [&::-webkit-slider-thumb]:transition-transform
                    [&::-webkit-slider-thumb]:hover:scale-110"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>0%</span>
                  <span>+2%</span>
                </div>
              </div>
              
              {/* Impact Grid */}
              <div className="grid md:grid-cols-2 gap-6">
                {/* Sector Impacts */}
                <div>
                  <h4 className="text-sm font-medium text-muted-foreground mb-4">
                    Sector Impact
                  </h4>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-secondary" />
                        <span className="font-medium">Technology</span>
                      </div>
                      <span className={`font-bold ${parseFloat(techImpact) < 0 ? 'text-destructive' : 'text-success'}`}>
                        {techImpact}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-success" />
                        <span className="font-medium">Healthcare</span>
                      </div>
                      <span className={`font-bold ${parseFloat(healthImpact) < 0 ? 'text-destructive' : 'text-success'}`}>
                        {healthImpact}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-warning" />
                        <span className="font-medium">Energy</span>
                      </div>
                      <span className={`font-bold ${parseFloat(energyImpact) > 0 ? 'text-success' : 'text-destructive'}`}>
                        +{energyImpact}%
                      </span>
                    </div>
                  </div>
                </div>
                
                {/* Pointer to real, verified numbers - deliberately not a
                    fabricated "live" portfolio-metrics readout */}
                <div className="flex flex-col justify-center h-full">
                  <h4 className="text-sm font-medium text-muted-foreground mb-4">
                    Does This Actually Work?
                  </h4>
                  <div className="p-4 bg-muted/50 rounded-lg border border-border">
                    <p className="text-sm text-foreground mb-3">
                      This slider illustrates the mechanism. For what the causal
                      adjustment actually does to backtested performance - real
                      numbers, not a demo - see the verified results below.
                    </p>
                    <a href="#results" className="inline-flex items-center gap-1.5 text-sm font-medium text-secondary hover:underline">
                      View verified backtest results
                      <ArrowDown className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              </div>
            </div>
            
            {/* CTA Footer */}
            <div className="px-8 py-4 bg-muted/30 border-t border-border flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                This is a simplified demo. Full analysis includes 50+ economic factors.
              </p>
              <Link to="/register">
                <Button variant="ghost" className="text-foreground hover:bg-accent/10">
                  Get Started
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
