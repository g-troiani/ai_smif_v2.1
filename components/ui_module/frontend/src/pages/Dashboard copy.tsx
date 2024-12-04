import React from 'react';
import { ArrowUpIcon } from '@heroicons/react/24/solid';
+ import DashboardMetrics from '../components/dashboard/DashboardMetrics';

const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Stats Grid */}
-     <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
-       <div className="bg-white overflow-hidden shadow rounded-lg">
-         <div className="p-5">
-           <div className="flex items-center">
-             <div className="flex-1">
-               <div className="text-sm font-medium text-gray-500 truncate">Account Balance</div>
-               <div className="mt-1 text-3xl font-semibold text-gray-900">$0</div>
-             </div>
-           </div>
-         </div>
-       </div>
-
-       <div className="bg-white overflow-hidden shadow rounded-lg">
-         <div className="p-5">
-           <div className="flex items-center">
-             <div className="flex-1">
-               <div className="text-sm font-medium text-gray-500 truncate">Active Strategies</div>
-               <div className="mt-1 text-3xl font-semibold text-gray-900">0</div>
-             </div>
-           </div>
-         </div>
-       </div>
-
-       <div className="bg-white overflow-hidden shadow rounded-lg">
-         <div className="p-5">
-           <div className="flex items-center">
-             <div className="flex-1">
-               <div className="text-sm font-medium text-gray-500 truncate">Today's P&L</div>
-               <div className="mt-1 text-3xl font-semibold text-gray-900">--</div>
-             </div>
-           </div>
-         </div>
-       </div>
-
-       <div className="bg-white overflow-hidden shadow rounded-lg">
-         <div className="p-5">
-           <div className="flex items-center">
-             <div className="flex-1">
-               <div className="text-sm font-medium text-gray-500 truncate">Drawdown</div>
-               <div className="mt-1 text-3xl font-semibold text-gray-900">--</div>
-             </div>
-           </div>
-         </div>
-       </div>
-     </div>
+     <DashboardMetrics />

      {/* Charts Grid */}
      // ... rest of the code remains exactly the same