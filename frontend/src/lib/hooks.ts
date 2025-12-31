/**
 * React Query hooks for data fetching
 * Uses TanStack Query for caching and state management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  authApi,
  marketApi,
  portfolioApi,
  causalApi,
  scenarioApi,
  userApi,
  type User,
  type RegisterData,
  type Portfolio,
  type CreatePortfolioData,
  type CausalGraph,
  type CreateCausalGraphData,
  type OptimizationRequest,
  type BacktestRequest,
  type TreatmentEffectRequest,
  type RunScenarioRequest,
  type UpdateProfileData,
} from './api';

// ============================================
// Auth Hooks
// ============================================
export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: () => authApi.getCurrentUser(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (data) => {
      queryClient.setQueryData(['currentUser'], { user: data.user });
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (userData: RegisterData) => authApi.register(userData),
    onSuccess: (data) => {
      queryClient.setQueryData(['currentUser'], { user: data.user });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      queryClient.clear();
    },
  });
}

// ============================================
// Market Data Hooks
// ============================================
export function useMarketIndicators() {
  return useQuery({
    queryKey: ['marketIndicators'],
    queryFn: () => marketApi.getIndicators(),
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  });
}

export function useSectorPerformance(period: string = '1M') {
  return useQuery({
    queryKey: ['sectorPerformance', period],
    queryFn: () => marketApi.getSectorPerformance(period),
    staleTime: 5 * 60 * 1000,
  });
}

export function useHistoricalData(symbol: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['historicalData', symbol, startDate, endDate],
    queryFn: () => marketApi.getHistoricalData(symbol, startDate, endDate),
    staleTime: 30 * 60 * 1000, // 30 minutes
    enabled: !!symbol,
  });
}

export function useMacroData(series?: string) {
  return useQuery({
    queryKey: ['macroData', series],
    queryFn: () => marketApi.getMacroData(series),
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

export function useQuote(symbol: string) {
  return useQuery({
    queryKey: ['quote', symbol],
    queryFn: () => marketApi.getQuote(symbol),
    staleTime: 60 * 1000,
    enabled: !!symbol,
  });
}

export function useBenchmarkPerformance(period: string = '1Y') {
  return useQuery({
    queryKey: ['benchmarkPerformance', period],
    queryFn: () => marketApi.getBenchmarkPerformance(period),
    staleTime: 30 * 60 * 1000,
  });
}

export function useMarketCondition() {
  return useQuery({
    queryKey: ['marketCondition'],
    queryFn: () => marketApi.getMarketCondition(),
    staleTime: 30 * 60 * 1000,
  });
}

// ============================================
// Portfolio Hooks
// ============================================
export function usePortfolios() {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => portfolioApi.getAll(),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePortfolio(id: number) {
  return useQuery({
    queryKey: ['portfolio', id],
    queryFn: () => portfolioApi.getById(id),
    enabled: !!id,
  });
}

export function useCreatePortfolio() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (portfolio: CreatePortfolioData) => portfolioApi.create(portfolio),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
}

export function useUpdatePortfolio() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, portfolio }: { id: number; portfolio: Partial<Portfolio> }) =>
      portfolioApi.update(id, portfolio),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
      queryClient.invalidateQueries({ queryKey: ['portfolio', id] });
    },
  });
}

export function useDeletePortfolio() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: number) => portfolioApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] });
    },
  });
}

export function usePortfolioPerformance(id: number, period: string = '1Y') {
  return useQuery({
    queryKey: ['portfolioPerformance', id, period],
    queryFn: () => portfolioApi.getPerformance(id, period),
    enabled: !!id,
    staleTime: 30 * 60 * 1000,
  });
}

export function useOptimizePortfolio() {
  return useMutation({
    mutationFn: (data: OptimizationRequest) => portfolioApi.optimize(data),
  });
}

export function useBacktest() {
  return useMutation({
    mutationFn: (data: BacktestRequest) => portfolioApi.backtest(data),
  });
}

export function useSectors() {
  return useQuery({
    queryKey: ['sectors'],
    queryFn: () => portfolioApi.getSectors(),
    staleTime: Infinity, // Static data
  });
}

// ============================================
// Causal Analysis Hooks
// ============================================
export function useCausalGraphs() {
  return useQuery({
    queryKey: ['causalGraphs'],
    queryFn: () => causalApi.getGraphs(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCausalGraph(id: number) {
  return useQuery({
    queryKey: ['causalGraph', id],
    queryFn: () => causalApi.getGraphById(id),
    enabled: !!id,
  });
}

export function useCreateCausalGraph() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (graph: CreateCausalGraphData) => causalApi.createGraph(graph),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['causalGraphs'] });
    },
  });
}

export function useUpdateCausalGraph() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, graph }: { id: number; graph: Partial<CausalGraph> }) =>
      causalApi.updateGraph(id, graph),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['causalGraphs'] });
      queryClient.invalidateQueries({ queryKey: ['causalGraph', id] });
    },
  });
}

export function useDeleteCausalGraph() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: number) => causalApi.deleteGraph(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['causalGraphs'] });
    },
  });
}

export function useEstimateTreatmentEffects() {
  return useMutation({
    mutationFn: (data: TreatmentEffectRequest) => causalApi.estimateEffects(data),
  });
}

export function useSensitivityMatrix() {
  return useQuery({
    queryKey: ['sensitivityMatrix'],
    queryFn: () => causalApi.getSensitivityMatrix(),
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

export function useValidateDag() {
  return useMutation({
    mutationFn: (dagStructure: { nodes: any[]; edges: any[] }) =>
      causalApi.validateDag(dagStructure),
  });
}

export function useEconomicFactors() {
  return useQuery({
    queryKey: ['economicFactors'],
    queryFn: () => causalApi.getEconomicFactors(),
    staleTime: Infinity, // Static data
  });
}

// ============================================
// Scenario Hooks
// ============================================
export function useScenarios() {
  return useQuery({
    queryKey: ['scenarios'],
    queryFn: () => scenarioApi.getAll(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useScenario(id: number) {
  return useQuery({
    queryKey: ['scenario', id],
    queryFn: () => scenarioApi.getById(id),
    enabled: !!id,
  });
}

export function useDeleteScenario() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (id: number) => scenarioApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scenarios'] });
    },
  });
}

export function useRunScenario() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: RunScenarioRequest) => scenarioApi.run(data),
    onSuccess: (_, variables) => {
      if (variables.save_results) {
        queryClient.invalidateQueries({ queryKey: ['scenarios'] });
      }
    },
  });
}

export function usePresetScenarios() {
  return useQuery({
    queryKey: ['presetScenarios'],
    queryFn: () => scenarioApi.getPresets(),
    staleTime: Infinity, // Static data
  });
}

export function useRunPresetScenario() {
  return useMutation({
    mutationFn: ({ presetId, portfolioWeights }: { presetId: string; portfolioWeights?: Record<string, number> }) =>
      scenarioApi.runPreset(presetId, portfolioWeights),
  });
}

export function useCompareScenarios() {
  return useMutation({
    mutationFn: (data: { scenarios: { name: string; parameters: Record<string, { change: number }> }[]; portfolio_weights?: Record<string, number> }) =>
      scenarioApi.compare(data),
  });
}

// ============================================
// User Hooks
// ============================================
export function useUserProfile() {
  return useQuery({
    queryKey: ['userProfile'],
    queryFn: () => userApi.getProfile(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: UpdateProfileData) => userApi.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userProfile'] });
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
    },
  });
}

export function useUserSettings() {
  return useQuery({
    queryKey: ['userSettings'],
    queryFn: () => userApi.getSettings(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useUserPerformance() {
  return useQuery({
    queryKey: ['userPerformance'],
    queryFn: () => userApi.getPerformance(),
    staleTime: 5 * 60 * 1000,
  });
}
