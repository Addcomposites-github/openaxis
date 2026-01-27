import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ChartBarIcon,
  ClockIcon,
  CubeIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

interface DashboardStats {
  totalProjects: number;
  activeJobs: number;
  totalPrintTime: number;
  completedParts: number;
}

interface RecentProject {
  id: string;
  name: string;
  process: string;
  lastModified: string;
  status: 'completed' | 'in_progress' | 'failed';
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats>({
    totalProjects: 0,
    activeJobs: 0,
    totalPrintTime: 0,
    completedParts: 0,
  });

  const [recentProjects, setRecentProjects] = useState<RecentProject[]>([]);

  useEffect(() => {
    // TODO: Load dashboard data from Python backend
    setStats({
      totalProjects: 12,
      activeJobs: 2,
      totalPrintTime: 156.5,
      completedParts: 48,
    });

    setRecentProjects([
      {
        id: '1',
        name: 'Bracket Assembly',
        process: 'WAAM',
        lastModified: '2 hours ago',
        status: 'completed',
      },
      {
        id: '2',
        name: 'Large Vessel',
        process: 'Pellet Extrusion',
        lastModified: '5 hours ago',
        status: 'in_progress',
      },
      {
        id: '3',
        name: 'Mold Core',
        process: 'Milling',
        lastModified: '1 day ago',
        status: 'completed',
      },
    ]);
  }, []);

  const statCards = [
    {
      name: 'Total Projects',
      value: stats.totalProjects,
      icon: DocumentTextIcon,
      color: 'bg-blue-500',
    },
    {
      name: 'Active Jobs',
      value: stats.activeJobs,
      icon: ChartBarIcon,
      color: 'bg-green-500',
    },
    {
      name: 'Print Time (hrs)',
      value: stats.totalPrintTime.toFixed(1),
      icon: ClockIcon,
      color: 'bg-purple-500',
    },
    {
      name: 'Completed Parts',
      value: stats.completedParts,
      icon: CubeIcon,
      color: 'bg-orange-500',
    },
  ];

  const getStatusColor = (status: RecentProject['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'in_progress':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: RecentProject['status']) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'in_progress':
        return 'In Progress';
      case 'failed':
        return 'Failed';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.name}
              className="bg-white rounded-lg shadow-sm border border-gray-200 p-6"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
                </div>
                <div className={`${stat.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Projects */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Recent Projects</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {recentProjects.map((project) => (
            <div key={project.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-gray-900">{project.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {project.process} • {project.lastModified}
                  </p>
                </div>
                <span
                  className={`px-3 py-1 text-xs font-medium rounded-full ${getStatusColor(
                    project.status
                  )}`}
                >
                  {getStatusText(project.status)}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div className="px-6 py-4 border-t border-gray-200">
          <button className="text-sm font-medium text-blue-600 hover:text-blue-700">
            View all projects →
          </button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <button
          onClick={() => navigate('/projects')}
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-left hover:border-blue-500 hover:shadow-md transition-all"
        >
          <div className="flex items-center space-x-4">
            <div className="bg-blue-100 p-3 rounded-lg">
              <DocumentTextIcon className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">New Project</h3>
              <p className="text-xs text-gray-500 mt-1">Start a new manufacturing project</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => navigate('/geometry')}
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-left hover:border-blue-500 hover:shadow-md transition-all"
        >
          <div className="flex items-center space-x-4">
            <div className="bg-green-100 p-3 rounded-lg">
              <CubeIcon className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Import Geometry</h3>
              <p className="text-xs text-gray-500 mt-1">Load STL, STEP, or OBJ files</p>
            </div>
          </div>
        </button>

        <button
          onClick={() => navigate('/simulation')}
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-left hover:border-blue-500 hover:shadow-md transition-all"
        >
          <div className="flex items-center space-x-4">
            <div className="bg-purple-100 p-3 rounded-lg">
              <ChartBarIcon className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">View Analytics</h3>
              <p className="text-xs text-gray-500 mt-1">Review process performance</p>
            </div>
          </div>
        </button>
      </div>
    </div>
  );
}
