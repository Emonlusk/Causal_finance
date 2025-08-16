import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ApiResponse<T> {
  status: 'success' | 'error';
  data?: T;
  error?: string;
}

export const financialApi = {
  // Get sample dataset
  getSampleData: async () => {
    try {
      const response = await api.get<ApiResponse<any>>('/sample-data');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch sample data');
    }
  },

  // Upload data file
  uploadData: async (file: File) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.post<ApiResponse<any>>('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to upload data');
    }
  },

  // Simulate effects
  simulateEffects: async (fedRate: number) => {
    try {
      const response = await api.post<ApiResponse<any>>('/simulate', { fed_rate: fedRate });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to simulate effects');
    }
  },

  // Generate portfolio
  generatePortfolio: async (allowShort: boolean) => {
    try {
      const response = await api.post<ApiResponse<any>>('/portfolio', { allow_short: allowShort });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to generate portfolio');
    }
  },

  // Run backtest
  runBacktest: async () => {
    try {
      const response = await api.post<ApiResponse<any>>('/backtest');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to run backtest');
    }
  },
};
