/**
 * API Configuration and Client Setup
 * Centralizes all API calls to the Flask backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

// Token management
let accessToken: string | null = localStorage.getItem('accessToken');
let refreshToken: string | null = localStorage.getItem('refreshToken');

export const setTokens = (access: string, refresh: string) => {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem('accessToken', access);
  localStorage.setItem('refreshToken', refresh);
};

export const clearTokens = () => {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
};

export const getAccessToken = () => accessToken;

// Generic fetch wrapper with auth
async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (accessToken) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle token refresh
  if (response.status === 401 && refreshToken) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
      const retryResponse = await fetch(url, { ...options, headers });
      if (!retryResponse.ok) {
        throw new Error(await retryResponse.text());
      }
      return retryResponse.json();
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || 'Request failed');
  }

  return response.json();
}

async function refreshAccessToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${refreshToken}`,
      },
    });

    if (response.ok) {
      const data = await response.json();
      accessToken = data.access_token;
      localStorage.setItem('accessToken', data.access_token);
      return true;
    }
    
    clearTokens();
    return false;
  } catch {
    clearTokens();
    return false;
  }
}

// ============================================
// Auth API
// ============================================
export const authApi = {
  login: async (email: string, password: string) => {
    const data = await fetchWithAuth<{
      message: string;
      user: User;
      access_token: string;
      refresh_token: string;
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  register: async (userData: RegisterData) => {
    const data = await fetchWithAuth<{
      message: string;
      user: User;
      access_token: string;
      refresh_token: string;
    }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },

  logout: async () => {
    try {
      await fetchWithAuth('/auth/logout', { method: 'POST' });
    } finally {
      clearTokens();
    }
  },

  getCurrentUser: () => fetchWithAuth<{ user: User }>('/auth/me'),
};

// ============================================
// Market Data API
// ============================================
export const marketApi = {
  getIndicators: () => 
    fetchWithAuth<{ indicators: MarketIndicators }>('/market/indicators'),

  getSectorPerformance: (period: string = '1M') =>
    fetchWithAuth<{ period: string; sectors: SectorData[] }>(
      `/market/sectors?period=${period}`
    ),

  getHistoricalData: (symbol: string, startDate?: string, endDate?: string) =>
    fetchWithAuth<{ symbol: string; data: HistoricalData[] }>(
      `/market/historical?symbol=${symbol}${startDate ? `&start_date=${startDate}` : ''}${endDate ? `&end_date=${endDate}` : ''}`
    ),

  getMacroData: (series?: string) =>
    fetchWithAuth<{ macro_data: MacroData }>(
      `/market/macro${series ? `?series=${series}` : ''}`
    ),

  getQuote: (symbol: string) =>
    fetchWithAuth<{ symbol: string; quote: QuoteData }>(`/market/quote/${symbol}`),

  getBenchmarkPerformance: (period: string = '1Y') =>
    fetchWithAuth<BenchmarkData>(`/market/benchmark?period=${period}`),

  getMarketCondition: () =>
    fetchWithAuth<{ condition: MarketCondition }>('/market/condition'),
};

// ============================================
// Portfolio API
// ============================================
export const portfolioApi = {
  getAll: () => 
    fetchWithAuth<{ portfolios: Portfolio[] }>('/portfolios/'),

  getById: (id: number) =>
    fetchWithAuth<{ portfolio: Portfolio }>(`/portfolios/${id}`),

  create: (portfolio: CreatePortfolioData) =>
    fetchWithAuth<{ message: string; portfolio: Portfolio }>('/portfolios/', {
      method: 'POST',
      body: JSON.stringify(portfolio),
    }),

  update: (id: number, portfolio: Partial<Portfolio>) =>
    fetchWithAuth<{ message: string; portfolio: Portfolio }>(`/portfolios/${id}`, {
      method: 'PUT',
      body: JSON.stringify(portfolio),
    }),

  delete: (id: number) =>
    fetchWithAuth<{ message: string }>(`/portfolios/${id}`, {
      method: 'DELETE',
    }),

  getPerformance: (id: number, period: string = '1Y') =>
    fetchWithAuth<PortfolioPerformance>(
      `/portfolios/${id}/performance?period=${period}`
    ),

  optimize: (data: OptimizationRequest) =>
    fetchWithAuth<OptimizationResult>('/portfolios/optimize', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  backtest: (data: BacktestRequest) =>
    fetchWithAuth<BacktestResult>('/portfolios/backtest', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSectors: () =>
    fetchWithAuth<{ sectors: Record<string, SectorInfo> }>('/portfolios/sectors'),
};

// ============================================
// Causal Analysis API
// ============================================
export const causalApi = {
  getGraphs: () =>
    fetchWithAuth<{ causal_graphs: CausalGraph[] }>('/causal/graphs'),

  getGraphById: (id: number) =>
    fetchWithAuth<{ causal_graph: CausalGraph }>(`/causal/graphs/${id}`),

  createGraph: (graph: CreateCausalGraphData) =>
    fetchWithAuth<{ message: string; causal_graph: CausalGraph }>('/causal/graphs', {
      method: 'POST',
      body: JSON.stringify(graph),
    }),

  updateGraph: (id: number, graph: Partial<CausalGraph>) =>
    fetchWithAuth<{ message: string; causal_graph: CausalGraph }>(`/causal/graphs/${id}`, {
      method: 'PUT',
      body: JSON.stringify(graph),
    }),

  deleteGraph: (id: number) =>
    fetchWithAuth<{ message: string }>(`/causal/graphs/${id}`, {
      method: 'DELETE',
    }),

  estimateEffects: (data: TreatmentEffectRequest) =>
    fetchWithAuth<TreatmentEffectResult>('/causal/estimate-effects', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getSensitivityMatrix: () =>
    fetchWithAuth<{ sensitivity_matrix: SensitivityMatrix }>('/causal/sensitivity-matrix'),

  validateDag: (dagStructure: DagStructure) =>
    fetchWithAuth<DagValidationResult>('/causal/validate-dag', {
      method: 'POST',
      body: JSON.stringify({ dag_structure: dagStructure }),
    }),

  getEconomicFactors: () =>
    fetchWithAuth<{ economic_factors: Record<string, EconomicFactor> }>('/causal/economic-factors'),
};

// ============================================
// Scenario API
// ============================================
export const scenarioApi = {
  getAll: () =>
    fetchWithAuth<{ scenarios: Scenario[] }>('/scenarios/'),

  getById: (id: number) =>
    fetchWithAuth<{ scenario: Scenario }>(`/scenarios/${id}`),

  create: (scenario: CreateScenarioData) =>
    fetchWithAuth<{ message: string; scenario: Scenario }>('/scenarios/', {
      method: 'POST',
      body: JSON.stringify(scenario),
    }),

  delete: (id: number) =>
    fetchWithAuth<{ message: string }>(`/scenarios/${id}`, {
      method: 'DELETE',
    }),

  run: (data: RunScenarioRequest) =>
    fetchWithAuth<ScenarioResult>('/scenarios/run', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getPresets: () =>
    fetchWithAuth<{ presets: Record<string, PresetScenario> }>('/scenarios/presets'),

  runPreset: (presetId: string, portfolioWeights?: Record<string, number>) =>
    fetchWithAuth<{ preset: PresetScenario; results: ScenarioResult }>(
      `/scenarios/presets/${presetId}/run`,
      {
        method: 'POST',
        body: JSON.stringify({ portfolio_weights: portfolioWeights }),
      }
    ),

  compare: (scenarios: CompareScenarioRequest) =>
    fetchWithAuth<CompareScenarioResult>('/scenarios/compare', {
      method: 'POST',
      body: JSON.stringify(scenarios),
    }),
};

// ============================================
// User API
// ============================================
export const userApi = {
  getProfile: () =>
    fetchWithAuth<{ user: User }>('/users/profile'),

  updateProfile: (data: UpdateProfileData) =>
    fetchWithAuth<{ message: string; user: User }>('/users/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  getSettings: () =>
    fetchWithAuth<{ settings: UserSettings }>('/users/settings'),

  getPerformance: () =>
    fetchWithAuth<{ performance: UserPerformance }>('/users/performance'),
};

// ============================================
// Type Definitions
// ============================================
export interface User {
  id: number;
  name: string;
  email?: string;
  risk_tolerance: string;
  investment_goals?: string;
  investment_horizon: string;
  plan: string;
  created_at: string;
  portfolio_count: number;
}

export interface RegisterData {
  email: string;
  password: string;
  name?: string;
  risk_tolerance?: string;
  investment_goals?: string;
  investment_horizon?: string;
}

export interface MarketIndicators {
  vix: { value: number; change: number; label: string; trend: string };
  fed_rate: { value: number; label: string; unit: string; trend: string };
  cpi: { value: number; change: number; label: string; unit: string; trend: string };
  treasury_10y: { value: number; change: number; label: string; unit: string; trend: string };
  sp500: { value: number; change: number; label: string; trend: string };
}

export interface SectorData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
}

export interface HistoricalData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface MacroData {
  [key: string]: {
    series_id: string;
    value: number;
    date: string;
  };
}

export interface QuoteData {
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap: number;
  pe_ratio: number;
  dividend_yield: number;
  fifty_two_week_high: number;
  fifty_two_week_low: number;
  timestamp: string;
}

export interface BenchmarkData {
  current_price: number;
  total_return: number;
  volatility: number;
  time_series: { date: string; close: number; return_pct: number }[];
}

export interface MarketCondition {
  state: 'bullish' | 'neutral' | 'bearish';
  score: number;
  description: string;
  factors: string[];
  indicators: MarketIndicators;
  timestamp: string;
}

export interface Portfolio {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  portfolio_type: string;
  weights: Record<string, number>;
  performance_metrics: {
    expected_return?: number;
    volatility?: number;
    sharpe_ratio?: number;
    max_drawdown?: number;
  };
  optimization_objective: string;
  time_horizon: string;
  causal_factors: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePortfolioData {
  name: string;
  description?: string;
  portfolio_type?: string;
  weights?: Record<string, number>;
  optimization_objective?: string;
  time_horizon?: string;
  causal_factors?: string[];
}

export interface PortfolioPerformance {
  portfolio_id: number;
  period: string;
  performance: {
    total_return: number;
    volatility: number;
    sharpe_ratio: number;
    max_drawdown: number;
    time_series: { date: string; return: number }[];
    start_date: string;
    end_date: string;
  };
}

export interface SectorInfo {
  name: string;
  color: string;
}

export interface OptimizationRequest {
  objective?: string;
  assets?: string[];
  use_causal?: boolean;
  causal_model_id?: number;
}

export interface OptimizationResult {
  traditional: {
    weights: Record<string, number>;
    metrics: {
      expected_return: number;
      volatility: number;
      sharpe_ratio: number;
      max_drawdown: number;
    };
  };
  causal: {
    weights: Record<string, number>;
    metrics: {
      expected_return: number;
      volatility: number;
      sharpe_ratio: number;
      max_drawdown: number;
    };
    adjustments: { asset: string; reason: string }[];
  };
  improvement: {
    return: number;
    volatility: number;
    sharpe: number;
  };
}

export interface BacktestRequest {
  weights: Record<string, number>;
  start_date?: string;
  end_date?: string;
}

export interface BacktestResult {
  start_date: string;
  end_date: string;
  total_return: number;
  annualized_return: number;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  time_series: { date: string; value: number }[];
}

export interface CausalGraph {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  dag_structure: DagStructure;
  treatment_effects: Record<string, TreatmentEffect>;
  confidence_scores: Record<string, number>;
  sector_sensitivity: Record<string, Record<string, number>>;
  validation_metrics: Record<string, number>;
  is_validated: boolean;
  created_at: string;
  updated_at: string;
}

export interface DagStructure {
  nodes: DagNode[];
  edges: DagEdge[];
}

export interface DagNode {
  id: string;
  label: string;
  type: 'economic' | 'asset' | 'outcome';
  x: number;
  y: number;
}

export interface DagEdge {
  from: string;
  to: string;
  strength: number;
  confidence?: number;
}

export interface CreateCausalGraphData {
  name: string;
  description?: string;
  dag_structure?: DagStructure;
}

export interface TreatmentEffect {
  effect: number;
  ci_lower: number;
  ci_upper: number;
  p_value: number;
}

export interface TreatmentEffectRequest {
  treatment: string;
  outcome: string;
  dag_structure?: DagStructure;
}

export interface TreatmentEffectResult {
  treatment: string;
  outcome: string;
  effect: number;
  effect_percentage: number;
  ci_lower: number;
  ci_upper: number;
  p_value: number;
  significant: boolean;
  method: string;
  interpretation: string;
}

export interface SensitivityMatrix {
  matrix: {
    sector: string;
    sector_key: string;
    [factor: string]: string | number;
  }[];
  factors: string[];
  sectors: string[];
  summary: Record<string, {
    mean: number;
    std: number;
    most_positive: string;
    most_negative: string;
  }>;
}

export interface DagValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  node_count: number;
  edge_count: number;
}

export interface EconomicFactor {
  label: string;
  fred_series: string;
  unit: string;
  description: string;
}

export interface Scenario {
  id: number;
  user_id: number;
  name: string;
  description?: string;
  scenario_type: string;
  parameters: Record<string, { change: number; current?: number }>;
  results: ScenarioResult;
  portfolio_id?: number;
  created_at: string;
  run_at?: string;
}

export interface CreateScenarioData {
  name: string;
  description?: string;
  scenario_type?: string;
  parameters?: Record<string, { change: number }>;
  portfolio_id?: number;
}

export interface RunScenarioRequest {
  name?: string;
  parameters: Record<string, { change: number }>;
  portfolio_weights?: Record<string, number>;
  save_results?: boolean;
}

export interface ScenarioResult {
  portfolio_impact: number;
  portfolio_impact_percent: number;
  causal_optimized_impact: number;
  causal_optimized_percent: number;
  traditional_impact: number;
  traditional_percent: number;
  sector_impacts: Record<string, number>;
  sector_breakdown: {
    sector: string;
    symbol: string;
    weight: number;
    current: number;
    causal: number;
    traditional: number;
    raw_impact: number;
  }[];
  recommendations: {
    immediate: {
      action: string;
      sector: string;
      symbol: string;
      current_weight: number;
      suggested_reduction?: number;
      suggested_increase?: number;
      reason: string;
    }[];
    strategic: {
      strategy: string;
      description: string;
      confidence: string;
    }[];
  };
}

export interface PresetScenario {
  name: string;
  description: string;
  parameters: Record<string, { change: number }>;
}

export interface CompareScenarioRequest {
  scenarios: { name: string; parameters: Record<string, { change: number }> }[];
  portfolio_weights?: Record<string, number>;
}

export interface CompareScenarioResult {
  comparisons: {
    name: string;
    parameters: Record<string, { change: number }>;
    results: ScenarioResult;
  }[];
}

export interface UpdateProfileData {
  name?: string;
  risk_tolerance?: string;
  investment_goals?: string;
  investment_horizon?: string;
}

export interface UserSettings {
  risk_tolerance: string;
  investment_goals?: string;
  investment_horizon: string;
  plan: string;
}

export interface UserPerformance {
  portfolio_count: number;
  portfolios: {
    id: number;
    name: string;
    type: string;
    expected_return: number;
    volatility: number;
    sharpe_ratio: number;
  }[];
}
