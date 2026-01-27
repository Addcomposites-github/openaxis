import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PlusIcon,
  MagnifyingGlassIcon,
  FolderIcon,
  TrashIcon,
  PencilIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline';
import NewProjectModal from '../components/NewProjectModal';
import { useProjectStore } from '../stores/projectStore';
import type { Project, ProcessType } from '../types';

export default function ProjectManager() {
  const navigate = useNavigate();
  const {
    projects,
    loadProjects,
    saveProject,
    deleteProject: deleteProjectFromStore,
    setCurrentProject,
  } = useProjectStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProcess, setSelectedProcess] = useState<string>('all');
  const [notification, setNotification] = useState<string | null>(null);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);

  // Load projects on mount
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const filteredProjects = projects.filter((project) => {
    const matchesSearch =
      project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesProcess = selectedProcess === 'all' || project.process === selectedProcess;
    return matchesSearch && matchesProcess;
  });

  const getStatusColor = (status: Project['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'ready':
        return 'bg-blue-100 text-blue-800';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status: Project['status']) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'ready':
        return 'Ready';
      case 'in_progress':
        return 'In Progress';
      case 'draft':
        return 'Draft';
      case 'failed':
        return 'Failed';
      default:
        return 'Unknown';
    }
  };

  const getProcessDisplayName = (process: ProcessType): string => {
    switch (process) {
      case 'waam':
        return 'WAAM';
      case 'pellet_extrusion':
        return 'Pellet Extrusion';
      case 'milling':
        return 'Milling';
      case 'hybrid':
        return 'Hybrid';
      default:
        return process;
    }
  };

  const handleEditProject = (projectId: string) => {
    const project = projects.find((p) => p.id === projectId);
    if (project) {
      setCurrentProject(project);
      setNotification(`Opening ${project.name}...`);
      setTimeout(() => {
        setNotification(null);
        navigate('/geometry');
      }, 500);
    }
  };

  const handleDuplicateProject = async (projectId: string) => {
    const project = projects.find((p) => p.id === projectId);
    if (project) {
      const duplicated: Project = {
        ...project,
        id: Date.now().toString(),
        name: `${project.name} (Copy)`,
        createdAt: new Date().toISOString(),
        modifiedAt: new Date().toISOString(),
        status: 'draft',
      };

      await saveProject(duplicated);
      setNotification(`${project.name} duplicated!`);
      setTimeout(() => setNotification(null), 2000);
    }
  };

  const handleDeleteProject = async (projectId: string, projectName: string) => {
    if (confirm(`Delete "${projectName}"? This cannot be undone.`)) {
      deleteProjectFromStore(projectId);
      setNotification(`${projectName} deleted`);
      setTimeout(() => setNotification(null), 2000);
    }
  };

  const handleNewProject = () => {
    setShowNewProjectModal(true);
  };

  const handleCreateProject = async (projectName: string, process: ProcessType) => {
    const newProject: Project = {
      id: Date.now().toString(),
      name: projectName,
      description: 'New manufacturing project',
      process: process,
      createdAt: new Date().toISOString(),
      modifiedAt: new Date().toISOString(),
      status: 'draft',
      settings: {
        units: 'metric',
        robotType: '',
        processParameters: {},
      },
    };

    await saveProject(newProject);
    setNotification(`Project "${projectName}" created!`);
    setTimeout(() => setNotification(null), 2000);
  };

  return (
    <div className="p-6 space-y-6">
      {/* Notification */}
      {notification && (
        <div className="fixed top-20 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-lg z-50">
          {notification}
        </div>
      )}

      {/* New Project Modal */}
      <NewProjectModal
        isOpen={showNewProjectModal}
        onClose={() => setShowNewProjectModal(false)}
        onSubmit={handleCreateProject}
      />

      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4 flex-1">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Process Filter */}
          <select
            value={selectedProcess}
            onChange={(e) => setSelectedProcess(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="all">All Processes</option>
            <option value="waam">WAAM</option>
            <option value="pellet_extrusion">Pellet Extrusion</option>
            <option value="milling">Milling</option>
            <option value="hybrid">Hybrid</option>
          </select>
        </div>

        {/* New Project Button */}
        <button
          onClick={handleNewProject}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          <span>New Project</span>
        </button>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProjects.map((project) => (
          <div
            key={project.id}
            className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
          >
            {/* Thumbnail */}
            <div className="h-48 bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center">
              {project.thumbnail ? (
                <img src={project.thumbnail} alt={project.name} className="w-full h-full object-cover" />
              ) : (
                <FolderIcon className="w-16 h-16 text-blue-400" />
              )}
            </div>

            {/* Content */}
            <div className="p-4">
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-lg font-semibold text-gray-900">{project.name}</h3>
                <span
                  className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                    project.status
                  )}`}
                >
                  {getStatusText(project.status)}
                </span>
              </div>

              <p className="text-sm text-gray-600 mb-3 line-clamp-2">{project.description}</p>

              <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
                <span className="font-medium text-blue-600">{getProcessDisplayName(project.process)}</span>
                <span>Modified: {new Date(project.modifiedAt).toLocaleDateString()}</span>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleEditProject(project.id)}
                  className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors"
                >
                  <PencilIcon className="w-4 h-4" />
                  <span className="text-sm font-medium">Edit</span>
                </button>
                <button
                  onClick={() => handleDuplicateProject(project.id)}
                  className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Duplicate"
                >
                  <DocumentDuplicateIcon className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDeleteProject(project.id, project.name)}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  title="Delete"
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {filteredProjects.length === 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
          <FolderIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No projects found</h3>
          <p className="text-gray-600 mb-6">
            {searchQuery || selectedProcess !== 'all'
              ? 'Try adjusting your search or filter'
              : 'Get started by creating your first project'}
          </p>
          <button
            onClick={handleNewProject}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Create New Project
          </button>
        </div>
      )}
    </div>
  );
}
