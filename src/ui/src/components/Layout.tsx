import { ReactNode, useState, useEffect, useCallback } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { checkHealth } from '../api/client';
import { useProjectStore } from '../stores/projectStore';
import html2canvas from 'html2canvas';
import {
  HomeIcon,
  FolderIcon,
  CubeIcon,
  ChartBarIcon,
  CogIcon,
  CameraIcon,
} from '@heroicons/react/24/outline';

interface LayoutProps {
  children: ReactNode;
}

interface NavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: HomeIcon },
  { name: 'Projects', path: '/projects', icon: FolderIcon },
  { name: 'Workspace', path: '/workspace', icon: CubeIcon },
  { name: 'Monitoring', path: '/monitoring', icon: ChartBarIcon },
  { name: 'Settings', path: '/settings', icon: CogIcon },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const loadProjects = useProjectStore((s) => s.loadProjects);
  const currentProject = useProjectStore((s) => s.currentProject);
  const [backendStatus, setBackendStatus] = useState<{
    connected: boolean;
    version: string;
    services: Record<string, boolean>;
  }>({ connected: false, version: '0.0.0', services: {} });

  // Auto-load projects on app mount — ensures a project is always selected
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    const check = async () => {
      const health = await checkHealth();
      setBackendStatus({
        connected: health.ok,
        version: health.version,
        services: health.services,
      });
    };
    check();
    const interval = setInterval(check, 10000); // Re-check every 10s
    return () => clearInterval(interval);
  }, []);

  const serviceCount = Object.values(backendStatus.services).filter(Boolean).length;
  const totalServices = Object.keys(backendStatus.services).length;

  const [capturing, setCapturing] = useState(false);

  const handleScreenshot = useCallback(async () => {
    setCapturing(true);
    try {
      // Capture full page including 3D canvases
      const canvas = await html2canvas(document.body, {
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#f9fafb',
        // html2canvas may not capture WebGL — we'll try to merge below
      });

      // Try to overlay any Three.js canvases (WebGL) onto the screenshot
      const webglCanvases = document.querySelectorAll('canvas[data-engine]');
      const ctx = canvas.getContext('2d');
      if (ctx) {
        webglCanvases.forEach((glCanvas) => {
          const el = glCanvas as HTMLCanvasElement;
          const rect = el.getBoundingClientRect();
          try {
            ctx.drawImage(el, rect.left, rect.top, rect.width, rect.height);
          } catch {
            // Cross-origin canvas — can't copy
          }
        });
      }

      // Download as PNG
      const dataUrl = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = `openaxis-screenshot-${new Date().toISOString().replace(/[:.]/g, '-')}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Screenshot capture failed:', err);
    } finally {
      setCapturing(false);
    }
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">OA</span>
            </div>
            <span className="text-xl font-semibold text-gray-900">OpenAxis</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-4 space-y-1">
          {navigation.map((item) => {
            const isActive = item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                to={item.path}
                className={`
                  flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors
                  ${
                    isActive
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  }
                `}
              >
                <Icon className="w-5 h-5 mr-3" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* Status Bar */}
        <div className="px-4 py-3 border-t border-gray-200">
          <div className="flex flex-col space-y-2">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span className="flex items-center">
                <span className={`w-2 h-2 rounded-full mr-2 ${backendStatus.connected ? 'bg-green-500' : 'bg-red-500'}`}></span>
                {backendStatus.connected ? 'Backend Connected' : 'Backend Offline'}
              </span>
              <span>v{backendStatus.version}</span>
            </div>
            {backendStatus.connected && totalServices > 0 && (
              <div className="text-xs text-gray-500">
                Services: {serviceCount}/{totalServices} active
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <div className="flex items-center space-x-4">
            <h1 className="text-lg font-semibold text-gray-900">
              {navigation.find((item) =>
                item.path === '/'
                  ? location.pathname === '/'
                  : location.pathname.startsWith(item.path)
              )?.name || 'OpenAxis'}
            </h1>
            {currentProject && (
              <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full border border-gray-200">
                {currentProject.name}
              </span>
            )}

          </div>

          <div className="flex items-center space-x-2 text-xs">
            {/* Screenshot button */}
            <button
              onClick={handleScreenshot}
              disabled={capturing}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="Capture screenshot"
            >
              <CameraIcon className={`w-5 h-5 ${capturing ? 'animate-pulse' : ''}`} />
            </button>

            {backendStatus.connected ? (
              <span className="px-3 py-1 bg-green-50 text-green-700 border border-green-200 rounded-full font-medium">
                Backend Online ({serviceCount} services)
              </span>
            ) : (
              <span className="px-3 py-1 bg-yellow-50 text-yellow-700 border border-yellow-200 rounded-full font-medium">
                Offline Mode - Start backend for full features
              </span>
            )}
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
