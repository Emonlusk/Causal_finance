import { useState } from "react";

export function MiniDAG() {
  const [hovered, setHovered] = useState<string | null>(null);

  const nodes = [
    { id: "a", x: 10, y: 50, label: "A" },
    { id: "b", x: 50, y: 25, label: "B" },
    { id: "c", x: 50, y: 75, label: "C" },
    { id: "d", x: 90, y: 50, label: "D" },
  ];

  const edges = [
    { from: "a", to: "b" },
    { from: "a", to: "c" },
    { from: "b", to: "d" },
    { from: "c", to: "d" },
  ];

  const getNode = (id: string) => nodes.find((n) => n.id === id)!;

  return (
    <div 
      className="h-16 relative"
      onMouseEnter={() => setHovered("active")}
      onMouseLeave={() => setHovered(null)}
    >
      <svg viewBox="0 0 100 100" className="w-full h-full">
        {/* Edges */}
        {edges.map((edge) => {
          const from = getNode(edge.from);
          const to = getNode(edge.to);
          return (
            <line
              key={`${edge.from}-${edge.to}`}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke={hovered ? "hsl(var(--primary))" : "hsl(var(--border))"}
              strokeWidth="2"
              className="transition-all duration-300"
            />
          );
        })}
        
        {/* Nodes */}
        {nodes.map((node) => (
          <g key={node.id}>
            <circle
              cx={node.x}
              cy={node.y}
              r={hovered ? 10 : 8}
              fill={hovered ? "hsl(var(--primary))" : "hsl(var(--muted))"}
              className="transition-all duration-300"
            />
            <text
              x={node.x}
              y={node.y}
              textAnchor="middle"
              dominantBaseline="central"
              fill={hovered ? "hsl(var(--primary-foreground))" : "hsl(var(--muted-foreground))"}
              fontSize="8"
              fontWeight="600"
              className="transition-all duration-300"
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
