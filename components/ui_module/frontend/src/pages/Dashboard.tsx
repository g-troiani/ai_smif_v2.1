// src/pages/Dashboard.tsx

import React from 'react';
import { ArrowUpIcon } from '@heroicons/react/24/solid';
import DashboardMetrics from '../components/dashboard/DashboardMetrics'; // Adjusted import path

const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <DashboardMetrics /> {/* DashboardMetrics now displays four metrics */}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Portfolio Performance Chart */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-6">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Portfolio Performance</h3>
            <div className="mt-5 h-96 relative">
              <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                No data available
              </div>
            </div>
          </div>
        </div>

        {/* Market Overview */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-6">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Market Overview</h3>
            <div className="mt-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-600">S&P 500</span>
                <div className="flex items-center text-green-600">
                  <ArrowUpIcon className="h-4 w-4 mr-1" />
                  <span>1.2%</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-600">Nasdaq</span>
                <div className="flex items-center text-green-600">
                  <ArrowUpIcon className="h-4 w-4 mr-1" />
                  <span>1.5%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
