import { useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';
import type { ProcessType } from '../types';

interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (projectName: string, process: ProcessType) => void;
}

export default function NewProjectModal({ isOpen, onClose, onSubmit }: NewProjectModalProps) {
  const [projectName, setProjectName] = useState('New Project');
  const [process, setProcess] = useState<ProcessType>('waam');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (projectName.trim()) {
      onSubmit(projectName.trim(), process);
      setProjectName('New Project');
      setProcess('waam');
      onClose();
    }
  };

  const handleCancel = () => {
    setProjectName('New Project');
    setProcess('waam');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={handleCancel}
      ></div>

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md p-6 mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Create New Project</h2>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Project Name
            </label>
            <input
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter project name"
              autoFocus
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Process Type
            </label>
            <select
              value={process}
              onChange={(e) => setProcess(e.target.value as ProcessType)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="waam">WAAM</option>
              <option value="pellet_extrusion">Pellet Extrusion</option>
              <option value="milling">Milling</option>
              <option value="hybrid">Hybrid (Multiple Processes)</option>
            </select>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={handleCancel}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Create Project
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
