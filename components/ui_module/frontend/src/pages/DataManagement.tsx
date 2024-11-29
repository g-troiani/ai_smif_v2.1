import React from 'react';

const DataManagement: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Data Management</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Data Configuration</h3>
          <form className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Data Interval</label>
              <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                <option>5 Minutes</option>
                <option>15 Minutes</option>
                <option>1 Hour</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Historical Period</label>
              <select className="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
                <option>5 Years</option>
              </select>
            </div>
            <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">
              Update Configuration
            </button>
          </form>
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Data Status</h3>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-500">Last Update</p>
              <p className="font-medium">Never</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Stream Status</p>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                Inactive
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataManagement;