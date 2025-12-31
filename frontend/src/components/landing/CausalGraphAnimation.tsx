import { useEffect, useState } from "react";

interface Node {
  id: string;
  x: number;
  y: number;
  label: string;
  type: "economic" | "asset" | "outcome";
  delay: number;
}

interface Edge {
  from: string;
  to: string;
  delay: number;
}

const nodes: Node[] = [
  { id: "rates", x: 15, y: 30, label: "Interest Rates", type: "economic", delay: 0 },
  { id: "inflation", x: 15, y: 70, label: "Inflation", type: "economic", delay: 200 },
  { id: "tech", x: 50, y: 20, label: "Tech", type: "asset", delay: 400 },
  { id: "health", x: 50, y: 50, label: "Healthcare", type: "asset", delay: 500 },
  { id: "energy", x: 50, y: 80, label: "Energy", type: "asset", delay: 600 },
  { id: "returns", x: 85, y: 50, label: "Portfolio Returns", type: "outcome", delay: 800 },
];

const edges: Edge[] = [
  { from: "rates", to: "tech", delay: 300 },
  { from: "rates", to: "health", delay: 400 },
  { from: "inflation", to: "energy", delay: 500 },
  { from: "inflation", to: "health", delay: 600 },
  { from: "tech", to: "returns", delay: 700 },
  { from: "health", to: "returns", delay: 800 },
  { from: "energy", to: "returns", delay: 900 },
];

const getNodePosition = (nodeId: string) => {
  const node = nodes.find((n) => n.id === nodeId);
  return node ? { x: node.x, y: node.y } : { x: 0, y: 0 };
};

const getNodeColor = (type: Node["type"]) => {
  switch (type) {
    case "economic":
      return "hsl(var(--primary))";
    case "asset":
      return "hsl(var(--accent))";
    case "outcome":
      return "hsl(var(--primary))";
    default:
      return "hsl(var(--muted))";
  }
};

const getNodeShape = (type: Node["type"], x: number, y: number) => {
  const size = type === "outcome" ? 14 : 10;
  switch (type) {
    case "economic":
      return (
        <rect
          x={x - size}
          y={y - size / 1.5}
          width={size * 2}
          height={size * 1.3}
          rx={3}
          fill={getNodeColor(type)}
        />
      );
    case "outcome":
      return (
        <polygon
          points={`${x},${y - size} ${x + size},${y} ${x},${y + size} ${x - size},${y}`}
          fill={getNodeColor(type)}
        />
      );
    default:
      return <circle cx={x} cy={y} r={size} fill={getNodeColor(type)} />;
  }
};

export function CausalGraphAnimation() {
  const [visibleNodes, setVisibleNodes] = useState<Set<string>>(new Set());
  const [visibleEdges, setVisibleEdges] = useState<Set<string>>(new Set());

  useEffect(() => {
    // Animate nodes appearing
    nodes.forEach((node) => {
      setTimeout(() => {
        setVisibleNodes((prev) => new Set([...prev, node.id]));
      }, node.delay + 500);
    });

    // Animate edges appearing
    edges.forEach((edge) => {
      setTimeout(() => {
        setVisibleEdges((prev) => new Set([...prev, `${edge.from}-${edge.to}`]));
      }, edge.delay + 800);
    });
  }, []);

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      <svg
        viewBox="0 0 100 100"
        className="w-full h-full opacity-20"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(var(--primary-foreground))" stopOpacity="0.6" />
            <stop offset="100%" stopColor="hsl(var(--primary-foreground))" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        {/* Edges */}
        {edges.map((edge) => {
          const from = getNodePosition(edge.from);
          const to = getNodePosition(edge.to);
          const edgeKey = `${edge.from}-${edge.to}`;
          const isVisible = visibleEdges.has(edgeKey);

          return (
            <line
              key={edgeKey}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="url(#edgeGradient)"
              strokeWidth="0.5"
              strokeDasharray="100"
              className={`transition-all duration-1000 ${
                isVisible ? "opacity-100" : "opacity-0"
              }`}
              style={{
                strokeDashoffset: isVisible ? 0 : 100,
                transition: "stroke-dashoffset 1s ease-out, opacity 0.5s ease-out",
              }}
            />
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          const isVisible = visibleNodes.has(node.id);

          return (
            <g
              key={node.id}
              className={`transition-all duration-500 ${
                isVisible ? "opacity-100" : "opacity-0"
              }`}
              style={{
                transform: isVisible ? "scale(1)" : "scale(0.5)",
                transformOrigin: `${node.x}% ${node.y}%`,
              }}
            >
              <g className="animate-node-pulse" style={{ animationDelay: `${node.delay}ms` }}>
                {getNodeShape(node.type, node.x, node.y)}
              </g>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
