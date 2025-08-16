'use client';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export default function Backtest() {
  // Sample data - in production, this would come from your Python backend
  const backtestData = Array.from({ length: 100 }, (_, i) => ({
    date: new Date(2020, 0, i + 1).toISOString().split('T')[0],
    causalReturn: Math.random() * 0.02 - 0.01 + 1,
    markowitzReturn: Math.random() * 0.015 - 0.0075 + 1,
    benchmarkReturn: Math.random() * 0.01 - 0.005 + 1,
  })).map((point, i, arr) => ({
    ...point,
    causalReturn: i === 0 ? 1 : arr[i - 1].causalReturn * point.causalReturn,
    markowitzReturn: i === 0 ? 1 : arr[i - 1].markowitzReturn * point.markowitzReturn,
    benchmarkReturn: i === 0 ? 1 : arr[i - 1].benchmarkReturn * point.benchmarkReturn,
  }));

  return (
    <div className="space-y-6">
      <div className="bg-white p-4 rounded-lg shadow-sm">
        <h3 className="text-lg font-medium mb-4">Portfolio Performance</h3>
        <div className="h-[400px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={backtestData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="causalReturn"
                name="Causal Portfolio"
                stroke="#2563eb"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="markowitzReturn"
                name="Markowitz Portfolio"
                stroke="#059669"
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="benchmarkReturn"
                name="S&P 500"
                stroke="#dc2626"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-lg shadow-sm">
          <h4 className="text-sm font-medium text-gray-500">Total Return</h4>
          <p className="text-2xl font-semibold text-blue-600">+45.2%</p>
          <p className="text-sm text-gray-500">vs. Benchmark +32.1%</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-sm">
          <h4 className="text-sm font-medium text-gray-500">Alpha</h4>
          <p className="text-2xl font-semibold text-green-600">+8.4%</p>
          <p className="text-sm text-gray-500">Annual Risk-Adjusted Return</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow-sm">
          <h4 className="text-sm font-medium text-gray-500">Information Ratio</h4>
          <p className="text-2xl font-semibold text-purple-600">1.23</p>
          <p className="text-sm text-gray-500">Risk-Adjusted Excess Return</p>
        </div>
      </div>
    </div>
  );
}
