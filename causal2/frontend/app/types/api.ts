export interface SampleData {
  stocks: string[];
  prices: Record<string, number[]>;
  dates: string[];
}

export interface SimulationResult {
  effects: Record<string, number>;
  confidence_intervals: Record<string, [number, number]>;
}

export interface Portfolio {
  weights: Record<string, number>;
  expected_return: number;
  risk: number;
}

export interface BacktestResult {
  returns: number[];
  dates: string[];
  metrics: {
    sharpe_ratio: number;
    max_drawdown: number;
    annualized_return: number;
    volatility: number;
  };
}
