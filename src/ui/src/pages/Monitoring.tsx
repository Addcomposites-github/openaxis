import { useState, useEffect, useRef } from 'react';
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ExclamationTriangleIcon,
  SignalIcon,
  SignalSlashIcon,
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
  ResponsiveContainer,
} from 'recharts';
import { apiClient } from '../api/client';

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
    cpuUsage: 0,
    memoryUsage: 0,
    diskUsage: 0,
    networkLatency: 0,
  });
  const [backendConnected, setBackendConnected] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const alertIdRef = useRef(0);

  useEffect(() => {
    // Initial data seed (empty)
    setSensorData([]);

    const fetchData = async () => {
      let sensorOk = false;
      let systemOk = false;

      // Fetch sensor data from backend
      try {
        const sensorRes = await apiClient.get('/api/monitoring/sensors', { timeout: 2000 });
        if (sensorRes.data?.status === 'success' && sensorRes.data?.data) {
          const d = sensorRes.data.data;
          setSensorData((prev) => {
            const newEntry: SensorData = {
              timestamp: d.timestamp ? d.timestamp * 1000 : Date.now(),
              temperature: d.temperature ?? 220,
              flowRate: d.flowRate ?? 10,
              pressure: d.pressure ?? 5,
            };
            const updated = [...prev, newEntry];
            // Keep last 60 data points (1 minute at 1s interval)
            return updated.slice(-60);
          });
          sensorOk = true;
        }
      } catch {
        // Offline fallback — generate random data locally
        setSensorData((prev) => {
          const newEntry: SensorData = {
            timestamp: Date.now(),
            temperature: 220 + Math.random() * 10,
            flowRate: 10 + Math.random() * 2,
            pressure: 5 + Math.random() * 1,
          };
          const updated = [...prev, newEntry];
          return updated.slice(-60);
        });
      }

      // Fetch system metrics from backend (uses psutil for real CPU/memory/disk)
      try {
        const sysRes = await apiClient.get('/api/monitoring/system', { timeout: 2000 });
        if (sysRes.data?.status === 'success' && sysRes.data?.data) {
          setSystemStatus(sysRes.data.data);
          systemOk = true;
        }
      } catch {
        // Offline fallback
        setSystemStatus({
          cpuUsage: 40 + Math.random() * 20,
          memoryUsage: 55 + Math.random() * 15,
          diskUsage: 35 + Math.random() * 10,
          networkLatency: 10 + Math.random() * 5,
        });
      }

      setBackendConnected(sensorOk || systemOk);

      // Generate alerts from sensor data
      setSensorData((prev) => {
        if (prev.length > 0) {
          const latest = prev[prev.length - 1];
          if (latest.temperature > 228) {
            const id = String(++alertIdRef.current);
            setAlerts((a) => [
              { id, level: 'warning', message: `Temperature high: ${latest.temperature.toFixed(1)}°C`, timestamp: 'just now' },
              ...a.slice(0, 9),
            ]);
          }
        }
        return prev;
      });
    };

    // Fetch immediately then every second
    fetchData();
    const interval = setInterval(fetchData, 1000);

    return () => clearInterval(interval);
  }, []);

  const dismissAlert = (id: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

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
      {/* Connection Status */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">System Monitoring</h2>
        <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-xs font-medium ${
          backendConnected
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-yellow-50 text-yellow-700 border border-yellow-200'
        }`}>
          {backendConnected ? (
            <SignalIcon className="w-4 h-4" />
          ) : (
            <SignalSlashIcon className="w-4 h-4" />
          )}
          <span>{backendConnected ? 'Connected to Backend' : 'Offline — Simulated Data'}</span>
        </div>
      </div>

      {/* System Status Cards — Real metrics from psutil when backend connected */}
      <div className="flex items-center gap-2 mb-1">
        <h3 className="text-sm font-semibold text-gray-700">System Metrics</h3>
        <span className="text-xs text-gray-400 font-mono">
          {backendConnected ? '(psutil — live)' : '(simulated)'}
        </span>
      </div>
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
              className={`h-2 rounded-full transition-all ${
                systemStatus.cpuUsage > 80 ? 'bg-red-500' : 'bg-blue-500'
              }`}
              style={{ width: `${Math.min(systemStatus.cpuUsage, 100)}%` }}
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
              className="bg-purple-500 h-2 rounded-full transition-all"
              style={{ width: `${Math.min(systemStatus.memoryUsage, 100)}%` }}
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
              className="bg-green-500 h-2 rounded-full transition-all"
              style={{ width: `${Math.min(systemStatus.diskUsage, 100)}%` }}
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

      {/* Sensor Charts — Simulated data (real sensor integration requires Robot Raconteur) */}
      <div className="flex items-center gap-2 mb-1">
        <h3 className="text-sm font-semibold text-gray-700">Sensor Preview</h3>
        <span className="text-xs text-gray-400 font-mono">(simulated)</span>
      </div>
      <p className="text-xs text-gray-400 mb-2">
        Real sensor integration requires Robot Raconteur hardware abstraction (Phase 4)
      </p>
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
                isAnimationActive={false}
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
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Alerts */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-900">System Alerts</h3>
          <button
            onClick={() => setAlerts([])}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            Clear All
          </button>
        </div>
        <div className="divide-y divide-gray-200">
          {alerts.length === 0 ? (
            <div className="px-6 py-6 text-center text-gray-400 text-sm">
              No alerts — system nominal
            </div>
          ) : (
            alerts.map((alert) => (
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
                  <button
                    onClick={() => dismissAlert(alert.id)}
                    className="text-sm font-medium hover:underline"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
