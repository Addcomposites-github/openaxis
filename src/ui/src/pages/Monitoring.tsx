import { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface SensorData {
  timestamp: number;
  temperature: number;
  flowRate: number;
  pressure: number;
}

interface SystemStatus {
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkLatency: number;
}

interface Alert {
  id: string;
  level: 'warning' | 'error' | 'info';
  message: string;
  timestamp: string;
}

export default function Monitoring() {
  const [sensorData, setSensorData] = useState<SensorData[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    cpuUsage: 45,
    memoryUsage: 62,
    diskUsage: 38,
    networkLatency: 12,
  });
  const [alerts, setAlerts] = useState<Alert[]>([
    {
      id: '1',
      level: 'warning',
      message: 'Temperature approaching upper limit',
      timestamp: '2 minutes ago',
    },
    {
      id: '2',
      level: 'info',
      message: 'Toolpath execution started',
      timestamp: '15 minutes ago',
    },
  ]);

  useEffect(() => {
    // Generate mock sensor data
    const generateData = () => {
      const now = Date.now();
      const data: SensorData[] = [];
      for (let i = 0; i < 50; i++) {
        data.push({
          timestamp: now - (50 - i) * 1000,
          temperature: 220 + Math.random() * 10,
          flowRate: 10 + Math.random() * 2,
          pressure: 5 + Math.random() * 1,
        });
      }
      return data;
    };

    setSensorData(generateData());

    // Update data every second
    const interval = setInterval(() => {
      setSensorData((prev) => {
        const newData = [...prev.slice(1)];
        newData.push({
          timestamp: Date.now(),
          temperature: 220 + Math.random() * 10,
          flowRate: 10 + Math.random() * 2,
          pressure: 5 + Math.random() * 1,
        });
        return newData;
      });

      // Update system status
      setSystemStatus({
        cpuUsage: 40 + Math.random() * 20,
        memoryUsage: 55 + Math.random() * 15,
        diskUsage: 35 + Math.random() * 10,
        networkLatency: 10 + Math.random() * 5,
      });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const getAlertColor = (level: Alert['level']) => {
    switch (level) {
      case 'error':
        return 'bg-red-100 border-red-300 text-red-800';
      case 'warning':
        return 'bg-yellow-100 border-yellow-300 text-yellow-800';
      case 'info':
        return 'bg-blue-100 border-blue-300 text-blue-800';
    }
  };

  const formatTimestamp = (timestamp: number): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      {/* System Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">CPU Usage</span>
            {systemStatus.cpuUsage > 80 ? (
              <ArrowTrendingUpIcon className="w-5 h-5 text-red-500" />
            ) : (
              <ArrowTrendingDownIcon className="w-5 h-5 text-green-500" />
            )}
          </div>
          <div className="flex items-end space-x-2">
            <span className="text-3xl font-bold text-gray-900">
              {systemStatus.cpuUsage.toFixed(0)}
            </span>
            <span className="text-gray-600 mb-1">%</span>
          </div>
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${
                systemStatus.cpuUsage > 80 ? 'bg-red-500' : 'bg-blue-500'
              }`}
              style={{ width: `${systemStatus.cpuUsage}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Memory</span>
            <ChartBarIcon className="w-5 h-5 text-gray-400" />
          </div>
          <div className="flex items-end space-x-2">
            <span className="text-3xl font-bold text-gray-900">
              {systemStatus.memoryUsage.toFixed(0)}
            </span>
            <span className="text-gray-600 mb-1">%</span>
          </div>
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-purple-500 h-2 rounded-full"
              style={{ width: `${systemStatus.memoryUsage}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Disk Usage</span>
            <ChartBarIcon className="w-5 h-5 text-gray-400" />
          </div>
          <div className="flex items-end space-x-2">
            <span className="text-3xl font-bold text-gray-900">
              {systemStatus.diskUsage.toFixed(0)}
            </span>
            <span className="text-gray-600 mb-1">%</span>
          </div>
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full"
              style={{ width: `${systemStatus.diskUsage}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-600">Network</span>
            <ChartBarIcon className="w-5 h-5 text-gray-400" />
          </div>
          <div className="flex items-end space-x-2">
            <span className="text-3xl font-bold text-gray-900">
              {systemStatus.networkLatency.toFixed(0)}
            </span>
            <span className="text-gray-600 mb-1">ms</span>
          </div>
          <div className="mt-2 text-xs text-gray-500">Latency</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Temperature Chart */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Temperature</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={sensorData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimestamp}
                stroke="#9ca3af"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                domain={[210, 240]}
                stroke="#9ca3af"
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                labelFormatter={(value) => formatTimestamp(value as number)}
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
              />
              <Line
                type="monotone"
                dataKey="temperature"
                stroke="#ef4444"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Flow Rate Chart */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Flow Rate</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={sensorData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatTimestamp}
                stroke="#9ca3af"
                style={{ fontSize: '12px' }}
              />
              <YAxis
                domain={[8, 14]}
                stroke="#9ca3af"
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                labelFormatter={(value) => formatTimestamp(value as number)}
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                }}
              />
              <Area
                type="monotone"
                dataKey="flowRate"
                stroke="#3b82f6"
                fill="#93c5fd"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Alerts */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">System Alerts</h3>
          <button className="text-xs text-blue-600 hover:text-blue-700 font-medium">
            Clear All
          </button>
        </div>
        <div className="divide-y divide-gray-200">
          {alerts.map((alert) => (
            <div key={alert.id} className="px-6 py-4">
              <div
                className={`flex items-start space-x-3 p-3 rounded-lg border ${getAlertColor(
                  alert.level
                )}`}
              >
                <ExclamationTriangleIcon className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium">{alert.message}</p>
                  <p className="text-xs mt-1 opacity-75">{alert.timestamp}</p>
                </div>
                <button className="text-sm font-medium hover:underline">Dismiss</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Current Job Info */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Current Job</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-xs text-gray-600 mb-1">Job Name</p>
            <p className="text-sm font-semibold text-gray-900">Large Vessel</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-1">Progress</p>
            <p className="text-sm font-semibold text-gray-900">48%</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-1">Elapsed Time</p>
            <p className="text-sm font-semibold text-gray-900">1h 23m</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-1">Remaining</p>
            <p className="text-sm font-semibold text-gray-900">1h 32m</p>
          </div>
        </div>
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div className="bg-blue-600 h-3 rounded-full" style={{ width: '48%' }}></div>
          </div>
        </div>
      </div>
    </div>
  );
}
