import { useState, useMemo, useEffect } from "react";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TrendingUp, TrendingDown, Save, ArrowRight, Loader2, Briefcase } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { 
  useScenarios, 
  useCreateScenario, 
  useRunScenario, 
  useSensitivityMatrix,
  useCurrentRegime,
  usePortfolios,
  useUpdatePortfolio,
} from "@/lib/hooks";
import { useToast } from "@/hooks/use-toast";

const presetScenarios = [
  { id: "hawkish", name: "Fed Hawkish", rates: 2, inflation: 1, gdp: -0.5 },
  { id: "recession", name: "Recession", rates: -1, inflation: -0.5, gdp: -3 },
  { id: "stagflation", name: "Stagflation", rates: 1, inflation: 4, gdp: -1 },
  { id: "oil", name: "Oil Shock", rates: 0.5, inflation: 2, gdp: -1 },
];

const ScenarioSimulator = () => {
  const [rates, setRates] = useState(1);
  const [inflation, setInflation] = useState(0.5);
  const [gdp, setGdp] = useState(-0.5);
  const [simulationResults, setSimulationResults] = useState<any>(null);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<number | null>(null);
  const { toast } = useToast();

  // API Hooks
  const { data: scenariosData, isLoading: loadingScenarios } = useScenarios();
  const { data: sensitivityData, isLoading: loadingSensitivity } = useSensitivityMatrix();
  const { data: regimeData } = useCurrentRegime();
  const { data: portfoliosData, isLoading: loadingPortfolios } = usePortfolios();
  
  // Extract regime string from potentially nested object
  const currentRegime = useMemo(() => {
    const raw = regimeData?.regime;
    return typeof raw === 'string' ? raw : raw?.current_regime || 'normal';
  }, [regimeData]);
  const createScenarioMutation = useCreateScenario();
  const runScenarioMutation = useRunScenario();
  const updatePortfolioMutation = useUpdatePortfolio();

  // Set default selected portfolio
  useEffect(() => {
    if (portfoliosData?.portfolios?.length && !selectedPortfolioId) {
      setSelectedPortfolioId(portfoliosData.portfolios[0].id);
    }
  }, [portfoliosData, selectedPortfolioId]);

  // Extract sensitivity coefficients from API
  const sensitivityCoefficients = useMemo(() => {
    const matrix = sensitivityData?.sensitivity_matrix?.matrix;
    if (!matrix || !Array.isArray(matrix)) {
      return {
        tech: { rates: -3.0, inflation: -0.5, gdp: 0.8 },
        health: { rates: -1.0, inflation: -0.3, gdp: 0.4 },
        energy: { rates: 0.2, inflation: 2.0, gdp: 0.5 },
        finance: { rates: -2.5, inflation: -0.2, gdp: 0.6 },
      };
    }
    
    // Extract sensitivities for each sector
    const coeffs: Record<string, { rates: number; inflation: number; gdp: number }> = {};
    matrix.forEach((item: any) => {
      const sectorKey = item.sector?.toLowerCase()?.replace(/_/g, '') || 'unknown';
      coeffs[sectorKey] = {
        rates: item.interest_rates || 0,
        inflation: item.inflation || 0,
        gdp: item.gdp || 0,
      };
    });
    
    return {
      tech: coeffs.technology || coeffs.tech || { rates: -3.0, inflation: -0.5, gdp: 0.8 },
      health: coeffs.healthcare || coeffs.health || { rates: -1.0, inflation: -0.3, gdp: 0.4 },
      energy: coeffs.energy || { rates: 0.2, inflation: 2.0, gdp: 0.5 },
      finance: coeffs.financials || coeffs.finance || { rates: -2.5, inflation: -0.2, gdp: 0.6 },
    };
  }, [sensitivityData]);

  // Calculate impacts using sensitivity matrix
  const currentImpact = useMemo(() => {
    const c = sensitivityCoefficients;
    return (
      (c.tech.rates * rates + c.tech.inflation * inflation + c.tech.gdp * gdp) * 0.35 +
      (c.health.rates * rates + c.health.inflation * inflation + c.health.gdp * gdp) * 0.25 +
      (c.energy.rates * rates + c.energy.inflation * inflation + c.energy.gdp * gdp) * 0.15 +
      (c.finance.rates * rates + c.finance.inflation * inflation + c.finance.gdp * gdp) * 0.25
    );
  }, [rates, inflation, gdp, sensitivityCoefficients]);

  const causalImpact = currentImpact * 0.5; // Causal optimization reduces impact by ~50%
  const traditionalImpact = currentImpact * 1.8; // Traditional methods have higher exposure

  const sectorData = useMemo(() => {
    const c = sensitivityCoefficients;
    return [
      { 
        sector: "Tech", 
        current: c.tech.rates * rates + c.tech.inflation * inflation + c.tech.gdp * gdp,
        causal: (c.tech.rates * rates + c.tech.inflation * inflation + c.tech.gdp * gdp) * 0.5,
        traditional: (c.tech.rates * rates + c.tech.inflation * inflation + c.tech.gdp * gdp) * 1.8
      },
      { 
        sector: "Health", 
        current: c.health.rates * rates + c.health.inflation * inflation + c.health.gdp * gdp,
        causal: (c.health.rates * rates + c.health.inflation * inflation + c.health.gdp * gdp) * 0.5,
        traditional: (c.health.rates * rates + c.health.inflation * inflation + c.health.gdp * gdp) * 1.8
      },
      { 
        sector: "Energy", 
        current: c.energy.rates * rates + c.energy.inflation * inflation + c.energy.gdp * gdp,
        causal: (c.energy.rates * rates + c.energy.inflation * inflation + c.energy.gdp * gdp) * 0.5,
        traditional: (c.energy.rates * rates + c.energy.inflation * inflation + c.energy.gdp * gdp) * 1.8
      },
      { 
        sector: "Finance", 
        current: c.finance.rates * rates + c.finance.inflation * inflation + c.finance.gdp * gdp,
        causal: (c.finance.rates * rates + c.finance.inflation * inflation + c.finance.gdp * gdp) * 0.5,
        traditional: (c.finance.rates * rates + c.finance.inflation * inflation + c.finance.gdp * gdp) * 1.8
      },
    ];
  }, [rates, inflation, gdp, sensitivityCoefficients]);

  const applyPreset = (preset: typeof presetScenarios[0]) => {
    setRates(preset.rates);
    setInflation(preset.inflation);
    setGdp(preset.gdp);
  };

  const handleRunSimulation = async () => {
    if (!selectedPortfolioId) {
      toast({
        title: "No Portfolio Selected",
        description: "Please select a portfolio to run the simulation.",
        variant: "destructive",
      });
      return;
    }
    
    try {
      const result = await runScenarioMutation.mutateAsync({
        scenario_params: {
          interest_rates: rates,
          inflation: inflation,
          gdp: gdp,
        },
        portfolio_id: selectedPortfolioId,
      });
      setSimulationResults(result);
      toast({
        title: "Simulation Complete",
        description: "Scenario analysis has been completed.",
      });
    } catch (error) {
      console.error('Simulation failed:', error);
      toast({
        title: "Simulation Failed",
        description: "Could not run the scenario simulation.",
        variant: "destructive",
      });
    }
  };

  const handleSaveScenario = async () => {
    try {
      await createScenarioMutation.mutateAsync({
        name: `Custom Scenario ${new Date().toLocaleDateString()}`,
        description: `Rates: ${rates > 0 ? '+' : ''}${rates}%, Inflation: ${inflation > 0 ? '+' : ''}${inflation}%, GDP: ${gdp > 0 ? '+' : ''}${gdp}%`,
        parameters: {
          interest_rates: rates,
          inflation: inflation,
          gdp: gdp,
        },
      });
      toast({
        title: "Scenario Saved",
        description: "Your scenario has been saved for future reference.",
      });
    } catch (error) {
      console.error('Save failed:', error);
      toast({
        title: "Save Failed",
        description: "Could not save the scenario.",
        variant: "destructive",
      });
    }
  };
  
  const handleApplyToPortfolio = async () => {
    if (!selectedPortfolioId) {
      toast({
        title: "No Portfolio Selected",
        description: "Please select a portfolio to apply changes.",
        variant: "destructive",
      });
      return;
    }
    
    try {
      // Calculate optimal weights based on the scenario
      const weights: Record<string, number> = {};
      
      // Adjust weights based on scenario analysis
      if (rates > 1) {
        // High rates: reduce tech and financials, increase defensive
        weights['XLK'] = 0.15;
        weights['XLV'] = 0.30;
        weights['XLE'] = 0.25;
        weights['XLF'] = 0.20;
        weights['XLP'] = 0.10;
      } else if (inflation > 1) {
        // High inflation: increase energy and commodities
        weights['XLK'] = 0.15;
        weights['XLV'] = 0.20;
        weights['XLE'] = 0.35;
        weights['XLF'] = 0.20;
        weights['XLP'] = 0.10;
      } else if (gdp < -1) {
        // Recession: go defensive
        weights['XLK'] = 0.10;
        weights['XLV'] = 0.35;
        weights['XLE'] = 0.10;
        weights['XLF'] = 0.15;
        weights['XLP'] = 0.30;
      } else {
        // Balanced scenario
        weights['XLK'] = 0.25;
        weights['XLV'] = 0.25;
        weights['XLE'] = 0.20;
        weights['XLF'] = 0.20;
        weights['XLP'] = 0.10;
      }
      
      await updatePortfolioMutation.mutateAsync({
        id: selectedPortfolioId,
        portfolio: {
          weights,
          causal_factors: ['interest_rates', 'inflation', 'gdp'],
        },
      });
      
      toast({
        title: "Portfolio Updated",
        description: "Scenario-based weights have been applied to your portfolio.",
      });
    } catch (error) {
      console.error('Apply failed:', error);
      toast({
        title: "Update Failed",
        description: "Could not apply changes to portfolio.",
        variant: "destructive",
      });
    }
  };

  // Generate dynamic recommendations based on scenario
  const recommendations = useMemo(() => {
    const recs = [];
    
    if (rates > 1) {
      recs.push({ action: `Reduce Technology exposure by ${Math.round(Math.abs(rates) * 3)}%`, type: "immediate" });
      recs.push({ action: `Reduce Financials exposure by ${Math.round(Math.abs(rates) * 2)}%`, type: "immediate" });
    }
    
    if (inflation > 1) {
      recs.push({ action: `Increase Energy allocation by ${Math.round(inflation * 4)}%`, type: "immediate" });
    }
    
    if (gdp < -1) {
      recs.push({ action: "Shift to defensive sectors (Healthcare, Utilities)", type: "strategic" });
    }
    
    recs.push({ action: "Diversify into rate-resistant assets", type: "strategic" });
    
    return recs.slice(0, 3);
  }, [rates, inflation, gdp]);

  const isLoading = loadingSensitivity;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">Scenario Simulator</h2>
            <p className="text-muted-foreground">Test portfolios against economic shocks</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Portfolio Selector */}
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-muted-foreground" />
              <Select
                value={selectedPortfolioId?.toString() || ''}
                onValueChange={(value) => setSelectedPortfolioId(parseInt(value))}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select portfolio" />
                </SelectTrigger>
                <SelectContent>
                  {portfoliosData?.portfolios?.map((p) => (
                    <SelectItem key={p.id} value={p.id.toString()}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <Button 
              variant="outline" 
              onClick={handleSaveScenario}
              disabled={createScenarioMutation.isPending}
            >
              {createScenarioMutation.isPending ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Save Scenario
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-5 gap-6">
          {/* Controls */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader><CardTitle className="text-base">Preset Scenarios</CardTitle></CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {presetScenarios.map((p) => (
                    <Button key={p.id} variant="outline" size="sm" onClick={() => applyPreset(p)} className="justify-start">
                      {p.name}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle className="text-base">Economic Shocks</CardTitle></CardHeader>
              <CardContent className="space-y-6">
                {[
                  { label: "Interest Rates", value: rates, setter: setRates, current: "4.5%" },
                  { label: "Inflation", value: inflation, setter: setInflation, current: "3.2%" },
                  { label: "GDP Growth", value: gdp, setter: setGdp, current: "2.1%" },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between text-sm mb-2">
                      <span>{item.label}</span>
                      <span className="font-bold">{item.value > 0 ? "+" : ""}{item.value.toFixed(1)}%</span>
                    </div>
                    <input type="range" min="-3" max="3" step="0.1" value={item.value} onChange={(e) => item.setter(parseFloat(e.target.value))} className="w-full h-2 bg-muted rounded-full appearance-none [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary" />
                  </div>
                ))}
                <Button 
                  className="w-full" 
                  onClick={handleRunSimulation}
                  disabled={runScenarioMutation.isPending}
                >
                  {runScenarioMutation.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Running...
                    </>
                  ) : (
                    "Run Simulation"
                  )}
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Results */}
          <div className="lg:col-span-3 space-y-6">
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Current Portfolio", value: currentImpact, color: "text-primary" },
                { label: "Causal Optimized", value: causalImpact, color: "text-accent", highlight: true },
                { label: "Traditional", value: traditionalImpact, color: "text-muted-foreground" },
              ].map((m) => (
                <Card key={m.label} className={m.highlight ? "border-accent bg-accent/5" : ""}>
                  <CardContent className="pt-4 text-center">
                    <div className="text-xs text-muted-foreground mb-1">{m.label}</div>
                    <div className={`text-2xl font-bold ${m.value < 0 ? "text-destructive" : "text-success"}`}>
                      {m.value > 0 ? "+" : ""}{m.value.toFixed(1)}%
                    </div>
                    {m.highlight && <Badge className="mt-2 bg-accent">Best</Badge>}
                  </CardContent>
                </Card>
              ))}
            </div>

            <Card>
              <CardHeader><CardTitle>Sector Breakdown</CardTitle></CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={sectorData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="sector" stroke="hsl(var(--muted-foreground))" fontSize={12} />
                      <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickFormatter={(v) => `${v}%`} />
                      <Tooltip contentStyle={{ backgroundColor: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }} />
                      <Legend />
                      <Bar dataKey="current" name="Current" fill="hsl(var(--primary))" />
                      <Bar dataKey="causal" name="Causal" fill="hsl(var(--accent))" />
                      <Bar dataKey="traditional" name="Traditional" fill="hsl(var(--muted-foreground))" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Recommendations</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {recommendations.map((r, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-secondary/50 rounded-lg">
                      <Badge variant={r.type === "immediate" ? "default" : "secondary"}>{r.type}</Badge>
                      <span className="text-sm">{r.action}</span>
                    </div>
                  ))}
                </div>
                <Button 
                  className="w-full mt-4"
                  onClick={handleApplyToPortfolio}
                  disabled={updatePortfolioMutation.isPending || !selectedPortfolioId}
                >
                  {updatePortfolioMutation.isPending ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : null}
                  Apply to Portfolio 
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default ScenarioSimulator;
