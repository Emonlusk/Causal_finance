'use client';
import { useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

export default function Portfolio() {
  const [allowShort, setAllowShort] = useState(false);
  
  // Sample data - in production, this would come from your Python backend
  const portfolioWeights = [
    { name: 'AAPL', weight: 0.25 },
    { name: 'MSFT', weight: 0.20 },
    { name: 'GOOGL', weight: 0.15 },
    { name: 'AMZN', weight: 0.15 },
    { name: 'FB', weight: 0.15 },
    { name: 'TSLA', weight: 0.10 },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium">Portfolio Allocation</h3>
        <div className="flex items-center">
          <input
            type="checkbox"
            id="allow-short"
            checked={allowShort}
            onChange={(e) => setAllowShort(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="allow-short" className="ml-2 text-sm text-gray-600">
            Allow Short Selling
          </label>
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg shadow-sm">
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={portfolioWeights}
                dataKey="weight"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={150}
                fill="#8884d8"
                label={({ name, value }) => `${name} (${(value * 100).toFixed(1)}%)`}
              >
                {portfolioWeights.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg shadow-sm">
        <h4 className="text-sm font-medium mb-4">Portfolio Statistics</h4>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Expected Return</p>
            <p className="text-lg font-medium">8.5%</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Volatility</p>
            <p className="text-lg font-medium">12.3%</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Sharpe Ratio</p>
            <p className="text-lg font-medium">0.69</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Max Drawdown</p>
            <p className="text-lg font-medium">-15.2%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
