import { useState, useCallback } from "react";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { 
  Plus, 
  Trash2, 
  Check, 
  X,
  Download,
  Save,
  RotateCcw
} from "lucide-react";

interface Node {
  id: string;
  x: number;
  y: number;
  label: string;
  type: "economic" | "asset" | "outcome";
}

interface Edge {
  from: string;
  to: string;
  strength: number;
}

const initialNodes: Node[] = [
  { id: "rates", x: 80, y: 100, label: "Interest Rates", type: "economic" },
  { id: "inflation", x: 80, y: 250, label: "Inflation", type: "economic" },
  { id: "gdp", x: 80, y: 400, label: "GDP Growth", type: "economic" },
  { id: "tech", x: 300, y: 80, label: "Technology", type: "asset" },
  { id: "health", x: 300, y: 180, label: "Healthcare", type: "asset" },
  { id: "energy", x: 300, y: 280, label: "Energy", type: "asset" },
  { id: "finance", x: 300, y: 380, label: "Financials", type: "asset" },
  { id: "returns", x: 520, y: 230, label: "Portfolio Returns", type: "outcome" },
];

const initialEdges: Edge[] = [
  { from: "rates", to: "tech", strength: -0.8 },
  { from: "rates", to: "finance", strength: -0.6 },
  { from: "rates", to: "health", strength: -0.2 },
  { from: "inflation", to: "energy", strength: 0.5 },
  { from: "inflation", to: "health", strength: -0.3 },
  { from: "gdp", to: "tech", strength: 0.6 },
  { from: "gdp", to: "finance", strength: 0.4 },
  { from: "tech", to: "returns", strength: 0.3 },
  { from: "health", to: "returns", strength: 0.25 },
  { from: "energy", to: "returns", strength: 0.2 },
  { from: "finance", to: "returns", strength: 0.25 },
];

const sectorSensitivity = [
  { sector: "Technology", effect: -0.8, confidence: 95, action: "reduce" },
  { sector: "Energy", effect: 0.3, confidence: 85, action: "increase" },
  { sector: "Healthcare", effect: -0.2, confidence: 90, action: "hold" },
  { sector: "Financials", effect: -0.6, confidence: 88, action: "reduce" },
];

const heatmapData = [
  { sector: "Technology", rates: -0.8, inflation: -0.2, gdp: 0.6, oil: -0.1 },
  { sector: "Healthcare", rates: -0.2, inflation: -0.3, gdp: 0.2, oil: 0.1 },
  { sector: "Energy", rates: 0.1, inflation: 0.5, gdp: 0.3, oil: 0.8 },
  { sector: "Financials", rates: -0.6, inflation: -0.1, gdp: 0.4, oil: 0.0 },
];

const CausalAnalysis = () => {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges] = useState<Edge[]>(initialEdges);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [draggingNode, setDraggingNode] = useState<string | null>(null);

  const getNodeColor = (type: Node["type"]) => {
    switch (type) {
      case "economic": return "fill-primary";
      case "asset": return "fill-accent";
      case "outcome": return "fill-primary";
      default: return "fill-muted";
    }
  };

  const getNodeShape = (node: Node) => {
    const size = node.type === "outcome" ? 20 : 16;
    switch (node.type) {
      case "economic":
        return (
          <rect
            x={node.x - size}
            y={node.y - size / 1.5}
            width={size * 2}
            height={size * 1.3}
            rx={4}
            className={`${getNodeColor(node.type)} ${selectedNode === node.id ? "stroke-foreground stroke-2" : ""}`}
          />
        );
      case "outcome":
        return (
          <polygon
            points={`${node.x},${node.y - size} ${node.x + size},${node.y} ${node.x},${node.y + size} ${node.x - size},${node.y}`}
            className={`${getNodeColor(node.type)} ${selectedNode === node.id ? "stroke-foreground stroke-2" : ""}`}
          />
        );
      default:
        return (
          <circle
            cx={node.x}
            cy={node.y}
            r={size}
            className={`${getNodeColor(node.type)} ${selectedNode === node.id ? "stroke-foreground stroke-2" : ""}`}
          />
        );
    }
  };

  const handleMouseDown = (nodeId: string) => {
    setDraggingNode(nodeId);
    setSelectedNode(nodeId);
  };

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!draggingNode) return;
    const svg = e.currentTarget;
    const rect = svg.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    setNodes((prev) =>
      prev.map((n) => (n.id === draggingNode ? { ...n, x, y } : n))
    );
  }, [draggingNode]);

  const handleMouseUp = () => {
    setDraggingNode(null);
  };

  const getHeatmapColor = (value: number) => {
    if (value > 0.3) return "bg-success text-success-foreground";
    if (value > 0) return "bg-success/50 text-foreground";
    if (value > -0.3) return "bg-destructive/50 text-foreground";
    return "bg-destructive text-destructive-foreground";
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">Causal Analysis</h2>
            <p className="text-muted-foreground">Build and explore causal relationships</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm">
              <RotateCcw className="w-4 h-4 mr-2" />
              Reset
            </Button>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button size="sm">
              <Save className="w-4 h-4 mr-2" />
              Save Graph
            </Button>
          </div>
        </div>

        <div className="grid lg:grid-cols-5 gap-6">
          {/* Causal Graph Canvas */}
          <Card className="lg:col-span-3">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle>Causal Graph Builder</CardTitle>
                <div className="flex items-center gap-4 text-xs">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded bg-primary" />
                    <span>Economic</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rounded-full bg-accent" />
                    <span>Asset</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 rotate-45 bg-primary" />
                    <span>Outcome</span>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="bg-secondary/30 rounded-lg border border-border overflow-hidden">
                <svg
                  width="100%"
                  height="450"
                  viewBox="0 0 600 450"
                  className="cursor-crosshair"
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                >
                  {/* Grid */}
                  <defs>
                    <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                      <path d="M 20 0 L 0 0 0 20" fill="none" stroke="hsl(var(--border))" strokeWidth="0.5" />
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="url(#grid)" />

                  {/* Edges */}
                  {edges.map((edge) => {
                    const fromNode = nodes.find((n) => n.id === edge.from);
                    const toNode = nodes.find((n) => n.id === edge.to);
                    if (!fromNode || !toNode) return null;
                    
                    return (
                      <line
                        key={`${edge.from}-${edge.to}`}
                        x1={fromNode.x}
                        y1={fromNode.y}
                        x2={toNode.x}
                        y2={toNode.y}
                        stroke={edge.strength > 0 ? "hsl(var(--success))" : "hsl(var(--destructive))"}
                        strokeWidth={Math.abs(edge.strength) * 3 + 1}
                        strokeOpacity={0.6}
                        markerEnd="url(#arrowhead)"
                      />
                    );
                  })}

                  {/* Nodes */}
                  {nodes.map((node) => (
                    <g
                      key={node.id}
                      className="cursor-move"
                      onMouseDown={() => handleMouseDown(node.id)}
                    >
                      {getNodeShape(node)}
                      <text
                        x={node.x}
                        y={node.y + (node.type === "economic" ? 30 : node.type === "outcome" ? 35 : 30)}
                        textAnchor="middle"
                        className="fill-foreground text-xs font-medium pointer-events-none"
                      >
                        {node.label}
                      </text>
                    </g>
                  ))}
                </svg>
              </div>

              {/* Toolbar */}
              <div className="flex items-center gap-2 mt-4">
                <Button variant="outline" size="sm">
                  <Plus className="w-4 h-4 mr-1" />
                  Add Node
                </Button>
                <Button variant="outline" size="sm" disabled={!selectedNode}>
                  <Trash2 className="w-4 h-4 mr-1" />
                  Remove
                </Button>
                <div className="flex-1" />
                <Badge variant={edges.length > 5 ? "default" : "secondary"}>
                  <Check className="w-3 h-3 mr-1" />
                  Graph Valid
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Analysis Panel */}
          <div className="lg:col-span-2 space-y-6">
            {/* Treatment Effects */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Treatment Effects</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Interest Rate → Tech Returns</div>
                    <div className="text-3xl font-bold text-destructive">-0.8%</div>
                    <div className="text-xs text-muted-foreground">per 1% increase</div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted-foreground">Confidence Interval</span>
                      <span>[-1.2%, -0.4%]</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden relative">
                      <div className="absolute left-1/4 right-1/4 h-full bg-primary/50 rounded-full" />
                      <div className="absolute left-1/2 w-1 h-full bg-primary -translate-x-1/2" />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Check className="w-4 h-4 text-success" />
                    <span className="text-sm">Statistically significant (p &lt; 0.05)</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Sector Sensitivity */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Sector Sensitivity</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {sectorSensitivity.map((row) => (
                    <div key={row.sector} className="flex items-center justify-between p-2 bg-secondary/50 rounded-lg">
                      <span className="text-sm font-medium">{row.sector}</span>
                      <div className="flex items-center gap-3">
                        <span className={`text-sm font-bold ${row.effect < 0 ? "text-destructive" : "text-success"}`}>
                          {row.effect > 0 ? "+" : ""}{row.effect}%
                        </span>
                        <Badge variant="outline" className="text-xs">{row.confidence}%</Badge>
                        {row.action === "reduce" && <Badge variant="destructive" className="text-xs">Reduce</Badge>}
                        {row.action === "increase" && <Badge className="bg-success text-xs">Increase</Badge>}
                        {row.action === "hold" && <Badge variant="secondary" className="text-xs">Hold</Badge>}
                      </div>
                    </div>
                  ))}
                </div>
                <Button variant="outline" className="w-full mt-4" size="sm">
                  Save to Portfolio Builder
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Sensitivity Heatmap */}
        <Card>
          <CardHeader>
            <CardTitle>Cross-Sector Sensitivity Matrix</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="text-left py-2 px-4 font-medium text-muted-foreground">Sector</th>
                    <th className="py-2 px-4 font-medium text-muted-foreground text-center">Interest Rates</th>
                    <th className="py-2 px-4 font-medium text-muted-foreground text-center">Inflation</th>
                    <th className="py-2 px-4 font-medium text-muted-foreground text-center">GDP</th>
                    <th className="py-2 px-4 font-medium text-muted-foreground text-center">Oil Prices</th>
                  </tr>
                </thead>
                <tbody>
                  {heatmapData.map((row) => (
                    <tr key={row.sector}>
                      <td className="py-2 px-4 font-medium">{row.sector}</td>
                      <td className="py-2 px-4">
                        <div className={`text-center py-1 px-2 rounded ${getHeatmapColor(row.rates)}`}>
                          {row.rates > 0 ? "+" : ""}{row.rates}
                        </div>
                      </td>
                      <td className="py-2 px-4">
                        <div className={`text-center py-1 px-2 rounded ${getHeatmapColor(row.inflation)}`}>
                          {row.inflation > 0 ? "+" : ""}{row.inflation}
                        </div>
                      </td>
                      <td className="py-2 px-4">
                        <div className={`text-center py-1 px-2 rounded ${getHeatmapColor(row.gdp)}`}>
                          {row.gdp > 0 ? "+" : ""}{row.gdp}
                        </div>
                      </td>
                      <td className="py-2 px-4">
                        <div className={`text-center py-1 px-2 rounded ${getHeatmapColor(row.oil)}`}>
                          {row.oil > 0 ? "+" : ""}{row.oil}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default CausalAnalysis;
