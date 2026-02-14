import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ChartBarIcon,
  ClockIcon,
  CubeIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { useProjectStore } from '../stores/projectStore';

export default function Dashboard() {
  const navigate = useNavigate();
  const { projects, isLoading, loadProjects } = useProjectStore();

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Compute stats from real project data
  const stats = useMemo(() => {
    const totalProjects = projects.length;
    const activeJobs = projects.filter(
      (p) => p.status === 'in_progress' || p.status === 'ready'
    ).length;
    const completedParts = projects.filter((p) => p.status === 'completed').length;
    // Estimate total print time from completed projects (mock estimate based on count)
    const totalPrintTime = completedParts * 3.5;
    return { totalProjects, activeJobs, completedParts, totalPrintTime };
  }, [projects]);

  // Sort projects by modifiedAt desc, take top 5
  const recentProjects = useMemo(() => {
    return [...projects]
      .sort((a, b) => new Date(b.modifiedAt).getTime() - new Date(a.modifiedAt).getTime())
      .slice(0, 5);
  }, [projects]);

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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'in_progress':
      case 'ready':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'in_progress':
        return 'In Progress';
      case 'ready':
        return 'Ready';
      case 'failed':
        return 'Failed';
      case 'draft':
        return 'Draft';
      default:
        return status;
    }
  };

  const formatRelativeDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 30) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    return date.toLocaleDateString();
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
                  <p className="text-3xl font-bold text-gray-900 mt-2">
                    {isLoading ? '...' : stat.value}
                  </p>
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
          {recentProjects.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              <p className="text-sm">No projects yet. Create your first project to get started.</p>
            </div>
          ) : (
            recentProjects.map((project) => (
              <div key={project.id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-gray-900">{project.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {project.process.replace('_', ' ').toUpperCase()} &bull;{' '}
                      {formatRelativeDate(project.modifiedAt)}
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
            ))
          )}
        </div>
        <div className="px-6 py-4 border-t border-gray-200">
          <button
            onClick={() => navigate('/projects')}
            className="text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            View all projects &rarr;
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
          onClick={() => navigate('/workspace?mode=geometry')}
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
          onClick={() => navigate('/workspace?mode=simulation')}
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-left hover:border-blue-500 hover:shadow-md transition-all"
        >
          <div className="flex items-center space-x-4">
            <div className="bg-purple-100 p-3 rounded-lg">
              <ChartBarIcon className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900">Robot Simulation</h3>
              <p className="text-xs text-gray-500 mt-1">Control robot joints interactively</p>
            </div>
          </div>
        </button>
      </div>
    </div>
  );
}
