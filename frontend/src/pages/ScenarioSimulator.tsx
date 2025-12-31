import { useState } from "react";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Save, Share2, ArrowRight } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

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

  const currentImpact = -(rates * 2.5 + inflation * 1.2 - gdp * 0.8);
  const causalImpact = -(rates * 1.2 + inflation * 0.4 - gdp * 0.5);
  const traditionalImpact = -(rates * 4.5 + inflation * 2.1 - gdp * 1.2);

  const sectorData = [
    { sector: "Tech", current: -(rates * 3), causal: -(rates * 1.5), traditional: -(rates * 5) },
    { sector: "Health", current: -(rates * 1), causal: -(rates * 0.5), traditional: -(rates * 2) },
    { sector: "Energy", current: inflation * 2, causal: inflation * 2.5, traditional: inflation * 1.5 },
    { sector: "Finance", current: -(rates * 2.5), causal: -(rates * 1.2), traditional: -(rates * 4) },
  ];

  const applyPreset = (preset: typeof presetScenarios[0]) => {
    setRates(preset.rates);
    setInflation(preset.inflation);
    setGdp(preset.gdp);
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Scenario Simulator</h2>
            <p className="text-muted-foreground">Test portfolios against economic shocks</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline"><Save className="w-4 h-4 mr-2" />Save</Button>
            <Button><Share2 className="w-4 h-4 mr-2" />Share</Button>
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
                <Button className="w-full">Run Simulation</Button>
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
                  {[
                    { action: "Reduce Technology exposure by 5%", type: "immediate" },
                    { action: "Increase Energy allocation by 8%", type: "immediate" },
                    { action: "Diversify into rate-resistant assets", type: "strategic" },
                  ].map((r, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-secondary/50 rounded-lg">
                      <Badge variant={r.type === "immediate" ? "default" : "secondary"}>{r.type}</Badge>
                      <span className="text-sm">{r.action}</span>
                    </div>
                  ))}
                </div>
                <Button className="w-full mt-4">Apply to Portfolio <ArrowRight className="w-4 h-4 ml-2" /></Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default ScenarioSimulator;
