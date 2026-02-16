/**
 * materialStore — Zustand store for material profiles.
 *
 * Manages the material library, selected material, and process type.
 * Fetches from backend API, falls back to built-in defaults.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ─── Types ────────────────────────────────────────────────────────────────────

export type ProcessType =
  | 'waam'
  | 'pellet_extrusion'
  | 'milling'
  | 'wire_laser'
  | 'concrete'
  | 'hybrid';

export type MaterialCategory = 'metal' | 'polymer' | 'concrete' | 'composite';

export interface MaterialProperties {
  density: number;          // kg/m3
  meltTemp: number | null;  // C
  beadWidth: number;        // mm
  layerHeight: number;      // mm
  printSpeed: number;       // mm/s
  travelSpeed: number;      // mm/s
  temperature: number | null; // C
  flowRate: number;         // multiplier
}

export interface SlicingDefaults {
  layerHeight: number;      // mm
  extrusionWidth: number;   // mm
  wallCount: number;
  infillDensity: number;    // 0-1
  infillPattern: string;
  printSpeed: number;       // mm/s
  travelSpeed: number;      // mm/s
}

export interface MaterialProfile {
  id: string;
  name: string;
  processType: ProcessType;
  category: MaterialCategory;
  description: string;
  isBuiltIn: boolean;
  properties: MaterialProperties;
  slicingDefaults: SlicingDefaults;
}

// ─── Process Type Display Info ───────────────────────────────────────────────

export interface ProcessTypeInfo {
  id: ProcessType;
  label: string;
  icon: string;  // emoji icon
  description: string;
}

export const PROCESS_TYPES: ProcessTypeInfo[] = [
  {
    id: 'waam',
    label: 'Wire Arc AM (WAAM)',
    icon: '⚡',
    description: 'Wire arc additive manufacturing using welding wire and arc energy.',
  },
  {
    id: 'pellet_extrusion',
    label: 'Pellet Extrusion',
    icon: '🔥',
    description: 'Large-format additive manufacturing using polymer pellets.',
  },
  {
    id: 'wire_laser',
    label: 'Wire Laser DED',
    icon: '🔆',
    description: 'Directed energy deposition using laser and metal wire.',
  },
  {
    id: 'concrete',
    label: 'Concrete Extrusion',
    icon: '🏗️',
    description: 'Large-scale construction using printable concrete mix.',
  },
  {
    id: 'milling',
    label: 'Milling (Subtractive)',
    icon: '⚙️',
    description: 'CNC-style subtractive manufacturing with robotic arm.',
  },
  {
    id: 'hybrid',
    label: 'Hybrid (Add + Sub)',
    icon: '🔄',
    description: 'Combined additive and subtractive in a single workflow.',
  },
];

// ─── Built-in Materials (fallback when backend is unavailable) ───────────────

const BUILT_IN_MATERIALS: MaterialProfile[] = [
  {
    id: 'waam_steel_er70s6',
    name: 'Steel ER70S-6',
    processType: 'waam',
    category: 'metal',
    description: 'Low-carbon steel welding wire. Most common WAAM material.',
    isBuiltIn: true,
    properties: {
      density: 7850, meltTemp: 1500, beadWidth: 5, layerHeight: 2,
      printSpeed: 10, travelSpeed: 80, temperature: null, flowRate: 1,
    },
    slicingDefaults: {
      layerHeight: 2, extrusionWidth: 5, wallCount: 1,
      infillDensity: 1, infillPattern: 'grid', printSpeed: 10, travelSpeed: 80,
    },
  },
  {
    id: 'waam_stainless_316l',
    name: 'Stainless Steel 316L',
    processType: 'waam',
    category: 'metal',
    description: 'Corrosion-resistant stainless steel for marine/chemical applications.',
    isBuiltIn: true,
    properties: {
      density: 7990, meltTemp: 1400, beadWidth: 4.5, layerHeight: 1.8,
      printSpeed: 8, travelSpeed: 70, temperature: null, flowRate: 1,
    },
    slicingDefaults: {
      layerHeight: 1.8, extrusionWidth: 4.5, wallCount: 1,
      infillDensity: 1, infillPattern: 'grid', printSpeed: 8, travelSpeed: 70,
    },
  },
  {
    id: 'waam_aluminum_5356',
    name: 'Aluminum 5356',
    processType: 'waam',
    category: 'metal',
    description: 'Aluminum-magnesium alloy for lightweight structures.',
    isBuiltIn: true,
    properties: {
      density: 2640, meltTemp: 660, beadWidth: 6, layerHeight: 2.5,
      printSpeed: 12, travelSpeed: 100, temperature: null, flowRate: 1,
    },
    slicingDefaults: {
      layerHeight: 2.5, extrusionWidth: 6, wallCount: 1,
      infillDensity: 1, infillPattern: 'grid', printSpeed: 12, travelSpeed: 100,
    },
  },
  {
    id: 'pellet_pla',
    name: 'PLA Pellets',
    processType: 'pellet_extrusion',
    category: 'polymer',
    description: 'Biodegradable polymer pellets for prototyping.',
    isBuiltIn: true,
    properties: {
      density: 1240, meltTemp: 180, beadWidth: 8, layerHeight: 3,
      printSpeed: 30, travelSpeed: 100, temperature: 200, flowRate: 1,
    },
    slicingDefaults: {
      layerHeight: 3, extrusionWidth: 8, wallCount: 2,
      infillDensity: 0.2, infillPattern: 'grid', printSpeed: 30, travelSpeed: 100,
    },
  },
  {
    id: 'pellet_petg',
    name: 'PETG Pellets',
    processType: 'pellet_extrusion',
    category: 'polymer',
    description: 'Chemical-resistant polymer for industrial parts.',
    isBuiltIn: true,
    properties: {
      density: 1270, meltTemp: 230, beadWidth: 8, layerHeight: 3,
      printSpeed: 25, travelSpeed: 90, temperature: 240, flowRate: 1,
    },
    slicingDefaults: {
      layerHeight: 3, extrusionWidth: 8, wallCount: 2,
      infillDensity: 0.2, infillPattern: 'grid', printSpeed: 25, travelSpeed: 90,
    },
  },
  {
    id: 'pellet_cf_pa',
    name: 'Carbon Fiber PA',
    processType: 'pellet_extrusion',
    category: 'composite',
    description: 'Carbon fiber reinforced nylon for tooling and molds.',
    isBuiltIn: true,
    properties: {
      density: 1200, meltTemp: 260, beadWidth: 10, layerHeight: 3.5,
      printSpeed: 20, travelSpeed: 80, temperature: 280, flowRate: 1,
    },
    slicingDefaults: {
      layerHeight: 3.5, extrusionWidth: 10, wallCount: 2,
      infillDensity: 0.3, infillPattern: 'grid', printSpeed: 20, travelSpeed: 80,
    },
  },
  {
    id: 'concrete_standard',
    name: 'Standard Concrete Mix',
    processType: 'concrete',
    category: 'concrete',
    description: 'Printable concrete for large-scale construction.',
    isBuiltIn: true,
    properties: {
      density: 2300, meltTemp: null, beadWidth: 30, layerHeight: 15,
      printSpeed: 50, travelSpeed: 100, temperature: null, flowRate: 1,
    },
    slicingDefaults: {
      layerHeight: 15, extrusionWidth: 30, wallCount: 2,
      infillDensity: 0, infillPattern: 'grid', printSpeed: 50, travelSpeed: 100,
    },
  },
];

// ─── Store ───────────────────────────────────────────────────────────────────

interface MaterialState {
  // Data
  materials: MaterialProfile[];
  isLoaded: boolean;
  isLoading: boolean;

  // Selection
  selectedProcessType: ProcessType;
  selectedMaterialId: string | null;

  // Computed
  selectedMaterial: MaterialProfile | null;

  // Actions
  setProcessType: (type: ProcessType) => void;
  setSelectedMaterial: (id: string | null) => void;
  loadMaterials: () => Promise<void>;
  getMaterialsForProcess: (processType: ProcessType) => MaterialProfile[];
}

export const useMaterialStore = create<MaterialState>()(
  persist(
    (set, get) => ({
      // Initial state
      materials: BUILT_IN_MATERIALS,
      isLoaded: false,
      isLoading: false,

      selectedProcessType: 'waam',
      selectedMaterialId: 'waam_steel_er70s6',

      get selectedMaterial(): MaterialProfile | null {
        const { materials, selectedMaterialId } = get();
        if (!selectedMaterialId) return null;
        return materials.find((m) => m.id === selectedMaterialId) || null;
      },

      setProcessType: (type: ProcessType) => {
        set({ selectedProcessType: type });
        // Auto-select first material for this process type
        const { materials } = get();
        const processMatls = materials.filter((m) => m.processType === type);
        if (processMatls.length > 0) {
          set({ selectedMaterialId: processMatls[0].id });
        } else {
          set({ selectedMaterialId: null });
        }
      },

      setSelectedMaterial: (id: string | null) => {
        set({ selectedMaterialId: id });
      },

      loadMaterials: async () => {
        const { isLoading } = get();
        if (isLoading) return;

        set({ isLoading: true });
        try {
          const response = await fetch('http://localhost:8000/api/materials');
          if (response.ok) {
            const json = await response.json();
            if (json.status === 'success' && Array.isArray(json.data)) {
              set({
                materials: json.data as MaterialProfile[],
                isLoaded: true,
                isLoading: false,
              });
              return;
            }
          }
        } catch (e) {
          console.warn('[MaterialStore] Backend unavailable, using built-in materials');
        }
        // Fallback to built-in
        set({
          materials: BUILT_IN_MATERIALS,
          isLoaded: true,
          isLoading: false,
        });
      },

      getMaterialsForProcess: (processType: ProcessType) => {
        return get().materials.filter((m) => m.processType === processType);
      },
    }),
    {
      name: 'openaxis-materials',
      partialize: (state) => ({
        selectedProcessType: state.selectedProcessType,
        selectedMaterialId: state.selectedMaterialId,
      }),
    },
  ),
);
