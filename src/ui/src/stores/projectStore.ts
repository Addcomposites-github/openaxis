import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type { Project, GeometryData, ToolpathData } from '../types';

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
        // Try to load from localStorage first
        const saved = localStorage.getItem('openaxis-projects');

        if (saved) {
          // Load saved projects
          const savedProjects: Project[] = JSON.parse(saved);
          // Auto-select persisted project or most recent
          const savedId = localStorage.getItem('openaxis-current-project-id');
          const autoSelect = savedProjects.find((p) => p.id === savedId)
            || savedProjects.sort((a, b) => new Date(b.modifiedAt).getTime() - new Date(a.modifiedAt).getTime())[0]
            || null;
          set((state) => {
            state.projects = savedProjects;
            state.currentProject = autoSelect;
            state.isLoading = false;
          });
          if (autoSelect) {
            localStorage.setItem('openaxis-current-project-id', autoSelect.id);
          }
        } else {
          // First time - load mock data
          const mockProjects: Project[] = [
            {
              id: '1',
              name: 'Bracket Assembly',
              description: 'Steel bracket for automotive application',
              process: 'waam',
              createdAt: '2024-01-15T00:00:00.000Z',
              modifiedAt: '2024-01-20T00:00:00.000Z',
              status: 'completed',
              settings: {
                units: 'metric',
                robotType: 'ABB IRB 6700',
                processParameters: {},
              },
            },
            {
              id: '2',
              name: 'Large Vessel',
              description: 'Composite vessel for industrial storage',
              process: 'pellet_extrusion',
              createdAt: '2024-01-18T00:00:00.000Z',
              modifiedAt: '2024-01-21T00:00:00.000Z',
              status: 'ready',
              settings: {
                units: 'metric',
                robotType: 'KUKA KR 500',
                processParameters: {},
              },
            },
            {
              id: '3',
              name: 'Mold Core',
              description: 'Precision mold for injection molding',
              process: 'milling',
              createdAt: '2024-01-10T00:00:00.000Z',
              modifiedAt: '2024-01-19T00:00:00.000Z',
              status: 'completed',
              settings: {
                units: 'metric',
                robotType: 'Fanuc M-20iA',
                processParameters: {},
              },
            },
            {
              id: '4',
              name: 'Prototype Housing',
              description: 'Concept housing for new product line',
              process: 'pellet_extrusion',
              createdAt: '2024-01-22T00:00:00.000Z',
              modifiedAt: '2024-01-22T00:00:00.000Z',
              status: 'draft',
              settings: {
                units: 'metric',
                robotType: '',
                processParameters: {},
              },
            },
          ];

          // Auto-select the most recently modified mock project
          const autoSelect = mockProjects.sort((a, b) => new Date(b.modifiedAt).getTime() - new Date(a.modifiedAt).getTime())[0] || null;
          set((state) => {
            state.projects = mockProjects;
            state.currentProject = autoSelect;
            state.isLoading = false;
          });
          if (autoSelect) {
            localStorage.setItem('openaxis-current-project-id', autoSelect.id);
          }

          // Save mock data to localStorage for next time
          localStorage.setItem('openaxis-projects', JSON.stringify(mockProjects));
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
        // TODO: Save to Python backend via IPC
        // await window.electron.invoke('save-project', project);

        set((state) => {
          const index = state.projects.findIndex((p) => p.id === project.id);
          if (index !== -1) {
            state.projects[index] = project;
          } else {
            state.projects.push(project);
          }
          state.isLoading = false;

          // Persist to localStorage
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
