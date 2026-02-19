import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { Project, GeometryData, ToolpathData } from '../types';
import { apiClient } from '../api/client';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  workspaceToolpath: any | null; // Raw backend ToolpathData for cross-page flow
  isLoading: boolean;
  error: string | null;

  // Actions
  setProjects: (projects: Project[]) => void;
  addProject: (project: Project) => void;
  updateProject: (id: string, updates: Partial<Project>) => void;
  deleteProject: (id: string) => void;
  setCurrentProject: (project: Project | null) => void;
  setWorkspaceToolpath: (data: any | null) => void;
  loadProjects: () => Promise<void>;
  saveProject: (project: Project) => Promise<void>;
  setGeometry: (geometry: GeometryData) => void;
  setToolpath: (toolpath: ToolpathData) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useProjectStore = create<ProjectState>()(
  immer((set, _get) => ({
    projects: [],
    currentProject: null,
    workspaceToolpath: null,
    isLoading: false,
    error: null,

    setProjects: (projects) =>
      set((state) => {
        state.projects = projects;
      }),

    addProject: (project) =>
      set((state) => {
        state.projects.push(project);
      }),

    updateProject: (id, updates) =>
      set((state) => {
        const index = state.projects.findIndex((p) => p.id === id);
        if (index !== -1) {
          state.projects[index] = { ...state.projects[index], ...updates };
        }
        if (state.currentProject?.id === id) {
          state.currentProject = { ...state.currentProject, ...updates };
        }
      }),

    deleteProject: (id) =>
      set((state) => {
        state.projects = state.projects.filter((p) => p.id !== id);
        if (state.currentProject?.id === id) {
          state.currentProject = null;
          localStorage.removeItem('openaxis-current-project-id');
        }

        // Persist to localStorage
        localStorage.setItem('openaxis-projects', JSON.stringify(state.projects));
      }),

    setCurrentProject: (project) =>
      set((state) => {
        state.currentProject = project;
        // Persist to localStorage so it survives refresh
        localStorage.setItem('openaxis-current-project-id', project?.id ?? '');
      }),

    setWorkspaceToolpath: (data) =>
      set((state) => {
        state.workspaceToolpath = data;
      }),

    loadProjects: async () => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });

      try {
        // Try backend first
        let projects: Project[] = [];
        let fromBackend = false;

        try {
          const res = await apiClient.get('/api/projects');
          if (res.data?.status === 'success' && Array.isArray(res.data?.data)) {
            projects = res.data.data;
            fromBackend = true;
          }
        } catch {
          // Backend unavailable — fall back to localStorage
        }

        if (!fromBackend) {
          const saved = localStorage.getItem('openaxis-projects');
          if (saved) {
            projects = JSON.parse(saved);
          }
          // No mock projects — empty state shows "Create your first project"
        }

        // Auto-select persisted project or most recent
        const savedId = localStorage.getItem('openaxis-current-project-id');
        const autoSelect = projects.find((p) => p.id === savedId)
          || projects.sort((a, b) => new Date(b.modifiedAt).getTime() - new Date(a.modifiedAt).getTime())[0]
          || null;

        set((state) => {
          state.projects = projects;
          state.currentProject = autoSelect;
          state.isLoading = false;
        });
        if (autoSelect) {
          localStorage.setItem('openaxis-current-project-id', autoSelect.id);
        }
      } catch (error) {
        set((state) => {
          state.error = error instanceof Error ? error.message : 'Failed to load projects';
          state.isLoading = false;
        });
      }
    },

    saveProject: async (project) => {
      set((state) => {
        state.isLoading = true;
        state.error = null;
      });

      try {
        // Try to save to backend
        try {
          await apiClient.post('/api/projects', project);
        } catch {
          // Backend unavailable — save locally only
        }

        set((state) => {
          const index = state.projects.findIndex((p) => p.id === project.id);
          if (index !== -1) {
            state.projects[index] = project;
          } else {
            state.projects.push(project);
          }
          state.isLoading = false;

          // Always persist to localStorage as cache
          localStorage.setItem('openaxis-projects', JSON.stringify(state.projects));
        });
      } catch (error) {
        set((state) => {
          state.error = error instanceof Error ? error.message : 'Failed to save project';
          state.isLoading = false;
        });
      }
    },

    setGeometry: (geometry) =>
      set((state) => {
        if (state.currentProject) {
          state.currentProject.geometry = geometry;
        }
      }),

    setToolpath: (toolpath) =>
      set((state) => {
        if (state.currentProject) {
          state.currentProject.toolpath = toolpath;
        }
      }),

    setLoading: (loading) =>
      set((state) => {
        state.isLoading = loading;
      }),

    setError: (error) =>
      set((state) => {
        state.error = error;
      }),
  }))
);
