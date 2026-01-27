import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  FolderIcon,
  CubeIcon,
  PencilIcon,
  PlayIcon,
  ChartBarIcon,
  CogIcon,
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
  { name: 'Geometry', path: '/geometry', icon: CubeIcon },
  { name: 'Toolpath', path: '/toolpath', icon: PencilIcon },
  { name: 'Simulation', path: '/simulation', icon: PlayIcon },
  { name: 'Monitoring', path: '/monitoring', icon: ChartBarIcon },
  { name: 'Settings', path: '/settings', icon: CogIcon },
];

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

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
            const isActive = location.pathname === item.path;
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
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                Backend Connected
              </span>
              <span>v0.1.0</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-green-600 font-medium">Phase 3 ✓</span>
              <span className="text-yellow-600 font-medium">Phase 4 ⋯</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <h1 className="text-lg font-semibold text-gray-900">
            {navigation.find((item) => item.path === location.pathname)?.name || 'OpenAxis'}
          </h1>

          <div className="flex items-center space-x-2 text-xs">
            <span className="px-3 py-1 bg-green-50 text-green-700 border border-green-200 rounded-full font-medium">
              UI Complete
            </span>
            <span className="px-3 py-1 bg-yellow-50 text-yellow-700 border border-yellow-200 rounded-full font-medium">
              Backend Integration In Progress
            </span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
