'use client';
import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

export default function Simulation() {
  const [fedRate, setFedRate] = useState(0);
  
  // Sample data - in production, this would come from your Python backend
  const simulationResults = [
    { name: 'AAPL', value: 2.5 },
    { name: 'MSFT', value: 1.8 },
    { name: 'GOOGL', value: 1.2 },
    { name: 'AMZN', value: -0.5 },
    { name: 'FB', value: 0.8 },
    { name: 'TSLA', value: -1.2 },
  ].map(item => ({
    ...item,
    value: item.value * (fedRate / 100)
  }));

  return (
    <div className="space-y-6">
      <div>
        <label
          htmlFor="fed-rate"
          className="block text-sm font-medium text-gray-700"
        >
          Federal Reserve Rate Change (%)
        </label>
        <input
          type="range"
          min="-2"
          max="2"
          step="0.25"
          value={fedRate}
          onChange={(e) => setFedRate(parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer mt-2"
        />
        <div className="text-center text-sm text-gray-600 mt-1">
          {fedRate > 0 ? "+" : ""}{fedRate}%
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg shadow-sm">
        <h3 className="text-lg font-medium mb-4">Predicted Impact on Stocks</h3>
        <div className="overflow-x-auto">
          <LineChart width={600} height={300} data={simulationResults}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#2563eb"
              name="Expected Return (%)"
            />
          </LineChart>
        </div>
      </div>
    </div>
  );
}
