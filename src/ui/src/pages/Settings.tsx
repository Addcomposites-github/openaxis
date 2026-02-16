import { useState, useEffect } from 'react';
import {
  CogIcon,
  ServerIcon,
  BellIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { checkHealth } from '../api/client';

const SETTINGS_KEY = 'openaxis-settings';

interface SettingsSection {
  id: string;
  name: string;
  icon: React.ComponentType<{ className?: string }>;
}

const sections: SettingsSection[] = [
  { id: 'general', name: 'General', icon: CogIcon },
  { id: 'robot', name: 'Robot Configuration', icon: ServerIcon },
  { id: 'notifications', name: 'Notifications', icon: BellIcon },
  { id: 'security', name: 'Security', icon: ShieldCheckIcon },
  { id: 'about', name: 'About', icon: DocumentTextIcon },
];

interface AppSettings {
  units: string;
  language: string;
  theme: string;
  autoSave: boolean;
  backupInterval: number;
  robotIP: string;
  robotPort: string;
  enableNotifications: boolean;
  notifyOnComplete: boolean;
  notifyOnError: boolean;
  soundEnabled: boolean;
}

const defaultSettings: AppSettings = {
  units: 'metric',
  language: 'en',
  theme: 'light',
  autoSave: true,
  backupInterval: 30,
  robotIP: '192.168.1.100',
  robotPort: '30001',
  enableNotifications: true,
  notifyOnComplete: true,
  notifyOnError: true,
  soundEnabled: true,
};

export default function Settings() {
  const [activeSection, setActiveSection] = useState('general');
  const [settings, setSettings] = useState<AppSettings>(defaultSettings);
  const [notification, setNotification] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'testing'>('disconnected');
  const [dirty, setDirty] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(SETTINGS_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        setSettings({ ...defaultSettings, ...parsed });
      }
    } catch {
      console.warn('Failed to load settings from localStorage');
    }
  }, []);

  const handleSettingChange = (key: keyof AppSettings, value: any) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setDirty(true);
  };

  const handleSave = () => {
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
      setDirty(false);
      setNotification('Settings saved!');
      setTimeout(() => setNotification(null), 2000);
    } catch {
      setNotification('Failed to save settings');
      setTimeout(() => setNotification(null), 3000);
    }
  };

  const handleReset = () => {
    setSettings(defaultSettings);
    setDirty(true);
    setNotification('Settings reset to defaults (click Save to persist)');
    setTimeout(() => setNotification(null), 3000);
  };

  const handleTestConnection = async () => {
    setConnectionStatus('testing');
    try {
      const health = await checkHealth();
      setConnectionStatus(health.ok ? 'connected' : 'disconnected');
      setNotification(health.ok ? `Backend connected (v${health.version})` : 'Backend unreachable');
    } catch {
      setConnectionStatus('disconnected');
      setNotification('Connection test failed');
    }
    setTimeout(() => setNotification(null), 3000);
  };

  const renderGeneralSettings = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Measurement Units
        </label>
        <select
          value={settings.units}
          onChange={(e) => handleSettingChange('units', e.target.value)}
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="metric">Metric (mm, kg)</option>
          <option value="imperial">Imperial (inch, lb)</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Language</label>
        <select
          value={settings.language}
          onChange={(e) => handleSettingChange('language', e.target.value)}
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="en">English</option>
          <option value="de">Deutsch</option>
          <option value="fr">Fran&ccedil;ais</option>
          <option value="es">Espa&ntilde;ol</option>
          <option value="zh">Chinese</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Theme</label>
        <select
          value={settings.theme}
          onChange={(e) => handleSettingChange('theme', e.target.value)}
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="light">Light</option>
          <option value="dark">Dark</option>
          <option value="auto">Auto (System)</option>
        </select>
      </div>

      <div className="border-t border-gray-200 pt-6">
        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.autoSave}
            onChange={(e) => handleSettingChange('autoSave', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm font-medium text-gray-700">Enable Auto-Save</span>
        </label>
        <p className="text-xs text-gray-500 ml-7 mt-1">
          Automatically save projects every few minutes
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Backup Interval (minutes)
        </label>
        <input
          type="number"
          value={settings.backupInterval}
          onChange={(e) => handleSettingChange('backupInterval', Number(e.target.value))}
          min="5"
          max="120"
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
    </div>
  );

  const renderRobotSettings = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Robot Type</label>
        <select className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
          <option>ABB IRB 6700</option>
          <option>KUKA KR 210</option>
          <option>Fanuc M-20iA</option>
          <option>Universal Robots UR10e</option>
          <option>Custom</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Robot IP Address
        </label>
        <input
          type="text"
          value={settings.robotIP}
          onChange={(e) => handleSettingChange('robotIP', e.target.value)}
          placeholder="192.168.1.100"
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Port</label>
        <input
          type="text"
          value={settings.robotPort}
          onChange={(e) => handleSettingChange('robotPort', e.target.value)}
          placeholder="30001"
          className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      <div className="border-t border-gray-200 pt-6">
        <button
          onClick={handleTestConnection}
          disabled={connectionStatus === 'testing'}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {connectionStatus === 'testing' ? 'Testing...' : 'Test Connection'}
        </button>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Connection Status</h4>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${
            connectionStatus === 'connected' ? 'bg-green-500' :
            connectionStatus === 'testing' ? 'bg-yellow-500 animate-pulse' :
            'bg-red-500'
          }`}></div>
          <span className="text-sm text-gray-700">
            {connectionStatus === 'connected' ? 'Connected' :
             connectionStatus === 'testing' ? 'Testing...' :
             'Disconnected'}
          </span>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Work Envelope Limits (mm)
        </label>
        <div className="grid grid-cols-2 gap-4 max-w-md">
          <div>
            <label className="text-xs text-gray-600">X Min</label>
            <input
              type="number"
              placeholder="-1000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-gray-600">X Max</label>
            <input
              type="number"
              placeholder="1000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-gray-600">Y Min</label>
            <input
              type="number"
              placeholder="-1000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-gray-600">Y Max</label>
            <input
              type="number"
              placeholder="1000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-gray-600">Z Min</label>
            <input
              type="number"
              placeholder="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mt-1"
            />
          </div>
          <div>
            <label className="text-xs text-gray-600">Z Max</label>
            <input
              type="number"
              placeholder="2000"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mt-1"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderNotificationSettings = () => (
    <div className="space-y-6">
      <div>
        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.enableNotifications}
            onChange={(e) =>
              handleSettingChange('enableNotifications', e.target.checked)
            }
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm font-medium text-gray-700">
            Enable Desktop Notifications
          </span>
        </label>
      </div>

      <div className="border-t border-gray-200 pt-6 space-y-4">
        <h4 className="text-sm font-semibold text-gray-900">Notify me when:</h4>

        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.notifyOnComplete}
            onChange={(e) => handleSettingChange('notifyOnComplete', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Job completes successfully</span>
        </label>

        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.notifyOnError}
            onChange={(e) => handleSettingChange('notifyOnError', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">An error occurs</span>
        </label>

        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Collision is detected</span>
        </label>

        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Temperature exceeds limits</span>
        </label>
      </div>

      <div className="border-t border-gray-200 pt-6">
        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.soundEnabled}
            onChange={(e) => handleSettingChange('soundEnabled', e.target.checked)}
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm font-medium text-gray-700">Play notification sounds</span>
        </label>
      </div>
    </div>
  );

  const renderSecuritySettings = () => (
    <div className="space-y-6">
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-4">Emergency Stop</h4>
        <p className="text-sm text-gray-600 mb-4">
          Configure emergency stop behavior and safety limits
        </p>
        <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
          Configure E-Stop
        </button>
      </div>

      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-4">Collision Detection</h4>
        <label className="flex items-center space-x-3 cursor-pointer mb-4">
          <input
            type="checkbox"
            defaultChecked
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Enable real-time collision checking</span>
        </label>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Safety Distance (mm)
          </label>
          <input
            type="number"
            defaultValue="50"
            min="0"
            max="200"
            className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-4">Access Control</h4>
        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Require authentication for robot control</span>
        </label>
      </div>
    </div>
  );

  const renderAboutSettings = () => (
    <div className="space-y-6">
      <div className="text-center py-8">
        <div className="w-20 h-20 bg-blue-600 rounded-lg flex items-center justify-center mx-auto mb-4">
          <span className="text-white font-bold text-3xl">OA</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">OpenAxis</h2>
        <p className="text-gray-600 mb-1">Version 0.1.0</p>
        <p className="text-sm text-gray-500">Open-source robotic hybrid manufacturing platform</p>
      </div>

      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-4">System Information</h4>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Platform:</span>
            <span className="font-medium text-gray-900">{navigator.platform || 'Unknown'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">User Agent:</span>
            <span className="font-medium text-gray-900 text-xs max-w-xs truncate">{navigator.userAgent.split(' ').pop()}</span>
          </div>
        </div>
      </div>

      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-sm font-semibold text-gray-900 mb-4">Links</h4>
        <div className="space-y-2">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="block text-sm text-blue-600 hover:text-blue-700 hover:underline"
          >
            GitHub Repository
          </a>
          <a
            href="#"
            className="block text-sm text-blue-600 hover:text-blue-700 hover:underline"
          >
            Documentation
          </a>
          <a
            href="#"
            className="block text-sm text-blue-600 hover:text-blue-700 hover:underline"
          >
            License (MIT)
          </a>
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    switch (activeSection) {
      case 'general':
        return renderGeneralSettings();
      case 'robot':
        return renderRobotSettings();
      case 'notifications':
        return renderNotificationSettings();
      case 'security':
        return renderSecuritySettings();
      case 'about':
        return renderAboutSettings();
      default:
        return null;
    }
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 p-4">
        <nav className="space-y-1">
          {sections.map((section) => {
            const Icon = section.icon;
            const isActive = activeSection === section.id;

            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`
                  w-full flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors
                  ${
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }
                `}
              >
                <Icon className="w-5 h-5 mr-3" />
                {section.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-3xl mx-auto p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            {sections.find((s) => s.id === activeSection)?.name}
          </h2>

          {/* Notification */}
          {notification && (
            <div className="mb-6 px-4 py-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg text-sm">
              {notification}
            </div>
          )}

          {renderContent()}

          {/* Save Button */}
          {activeSection !== 'about' && (
            <div className="mt-8 pt-6 border-t border-gray-200 flex items-center space-x-4">
              <button
                onClick={handleSave}
                className={`px-6 py-2 rounded-lg transition-colors ${
                  dirty
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-default'
                }`}
              >
                Save Changes
              </button>
              <button
                onClick={handleReset}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Reset to Defaults
              </button>
              {dirty && (
                <span className="text-xs text-yellow-600">Unsaved changes</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
