'use client';
import { useState } from 'react';
import CausalGraph from './components/CausalGraph';
import DataUpload from './components/DataUpload';
import Portfolio from './components/Portfolio';
import Backtest from './components/Backtest';
import Simulation from './components/Simulation';

export default function Home() {
  const [activeTab, setActiveTab] = useState('upload');

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-7xl mx-auto">
        <nav className="bg-white shadow-lg rounded-lg mb-6">
          <div className="flex space-x-4 p-4">
            <button
              onClick={() => setActiveTab('upload')}
              className={`px-4 py-2 rounded-md ${
                activeTab === 'upload'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              Data Upload
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              className={`px-4 py-2 rounded-md ${
                activeTab === 'graph'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              Causal Graph
            </button>
            <button
              onClick={() => setActiveTab('portfolio')}
              className={`px-4 py-2 rounded-md ${
                activeTab === 'portfolio'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              Portfolio
            </button>
            <button
              onClick={() => setActiveTab('simulation')}
              className={`px-4 py-2 rounded-md ${
                activeTab === 'simulation'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              Simulation
            </button>
            <button
              onClick={() => setActiveTab('backtest')}
              className={`px-4 py-2 rounded-md ${
                activeTab === 'backtest'
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100'
              }`}
            >
              Backtest
            </button>
          </div>
        </nav>

        <main className="bg-white shadow-lg rounded-lg p-6">
          {activeTab === 'upload' && <DataUpload />}
          {activeTab === 'graph' && <CausalGraph />}
          {activeTab === 'portfolio' && <Portfolio />}
          {activeTab === 'simulation' && <Simulation />}
          {activeTab === 'backtest' && <Backtest />}
        </main>
      </div>
    </div>
  );
}
