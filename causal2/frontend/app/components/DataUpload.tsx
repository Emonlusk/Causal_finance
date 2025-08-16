'use client';
import { useState } from 'react';
import { CloudArrowUpIcon, DocumentIcon } from '@heroicons/react/24/outline';

export default function DataUpload() {
  const [dragActive, setDragActive] = useState(false);
  
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      // Handle the upload
      console.log(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Get Started with Your Data</h2>
        <p className="text-gray-600 mb-8">
          Upload your financial data or use our sample dataset to explore the causal portfolio optimizer.
        </p>
      </div>

      <div
        className={`border-2 border-dashed rounded-lg p-12 text-center ${
          dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
        <div className="mt-4">
          <label htmlFor="file-upload" className="relative cursor-pointer">
            <span className="font-medium text-blue-600 hover:text-blue-500">
              Upload a file
            </span>
            <input
              id="file-upload"
              name="file-upload"
              type="file"
              className="sr-only"
              accept=".parquet,.csv"
            />
          </label>
          <p className="pl-1 text-gray-500">or drag and drop</p>
          <p className="text-xs text-gray-500">
            Supported formats: .parquet, .csv (Max 50MB)
          </p>
        </div>
      </div>

      <div className="mt-8">
        <button
          type="button"
          className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
        >
          <DocumentIcon className="h-5 w-5 mr-2 text-gray-400" />
          Use Sample Data
        </button>
      </div>

      <div className="mt-8 p-4 bg-blue-50 rounded-lg">
        <h3 className="text-sm font-medium text-blue-800">Expected Data Format:</h3>
        <p className="mt-2 text-sm text-blue-700">
          Your file should contain columns for date, symbol, price, return, and volume for stock data.
          Economic data should include fed_rate, inflation, gdp_growth, unemployment, and vix.
        </p>
      </div>
    </div>
  );
}
