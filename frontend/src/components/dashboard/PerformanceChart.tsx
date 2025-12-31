import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const generateData = () => {
  const data = [];
  let portfolio = 100;
  let causal = 100;
  let sp500 = 100;

  for (let i = 0; i < 12; i++) {
    const month = new Date(2024, i, 1).toLocaleString("default", { month: "short" });
    portfolio += (Math.random() - 0.3) * 8;
    causal += (Math.random() - 0.25) * 7;
    sp500 += (Math.random() - 0.35) * 6;
    
    data.push({
      month,
      portfolio: Math.round(portfolio * 10) / 10,
      causal: Math.round(causal * 10) / 10,
      sp500: Math.round(sp500 * 10) / 10,
    });
  }
  return data;
};

const data = generateData();

const timeframes = ["1M", "3M", "1Y", "All"];

export function PerformanceChart() {
  const [selectedTimeframe, setSelectedTimeframe] = useState("1Y");

  return (
    <Card className="col-span-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Performance Comparison</CardTitle>
        <div className="flex items-center gap-2">
          {timeframes.map((tf) => (
            <Button
              key={tf}
              variant={selectedTimeframe === tf ? "default" : "ghost"}
              size="sm"
              onClick={() => setSelectedTimeframe(tf)}
              className={selectedTimeframe === tf ? "" : "text-muted-foreground"}
            >
              {tf}
            </Button>
          ))}
        </div>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis 
                dataKey="month" 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                }}
                labelStyle={{ color: "hsl(var(--foreground))" }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="portfolio"
                name="Your Portfolio"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="causal"
                name="Causal Optimized"
                stroke="hsl(var(--accent))"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="sp500"
                name="S&P 500"
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
