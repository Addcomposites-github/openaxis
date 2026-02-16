/**
 * ProcessSetupSection — Process type and material selection.
 *
 * Shows process type cards, material dropdown filtered by process,
 * and a preview of the selected material's recommended parameters.
 */

import { useEffect } from 'react';
import {
  useMaterialStore,
  PROCESS_TYPES,
  type MaterialProfile,
} from '../../stores/materialStore';

export default function ProcessSetupSection() {
  const {
    materials,
    isLoaded,
    selectedProcessType,
    selectedMaterialId,
    setProcessType,
    setSelectedMaterial,
    loadMaterials,
  } = useMaterialStore();

  // Load materials on mount
  useEffect(() => {
    if (!isLoaded) {
      loadMaterials();
    }
  }, [isLoaded, loadMaterials]);

  const processMatls = materials.filter(
    (m) => m.processType === selectedProcessType,
  );
  const selectedMaterial = selectedMaterialId
    ? materials.find((m) => m.id === selectedMaterialId)
    : null;

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-1">
          Process Configuration
        </h3>
        <p className="text-xs text-gray-500">
          Select manufacturing process and material to auto-configure parameters.
        </p>
      </div>

      {/* Process Type Selection */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-2">
          Process Type
        </label>
        <div className="grid grid-cols-2 gap-2">
          {PROCESS_TYPES.map((pt) => (
            <button
              key={pt.id}
              onClick={() => setProcessType(pt.id)}
              className={`
                flex items-start gap-2 p-2.5 rounded-lg border text-left transition-all
                ${
                  selectedProcessType === pt.id
                    ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-200'
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                }
              `}
            >
              <span className="text-lg flex-shrink-0">{pt.icon}</span>
              <div className="min-w-0">
                <div className="text-xs font-medium text-gray-900 truncate">
                  {pt.label}
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Material Selection */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Material
        </label>
        {processMatls.length === 0 ? (
          <div className="text-xs text-gray-400 italic py-2">
            No materials available for this process type.
          </div>
        ) : (
          <select
            value={selectedMaterialId || ''}
            onChange={(e) => setSelectedMaterial(e.target.value || null)}
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Select material...</option>
            {processMatls.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
                {m.category !== 'metal' ? ` (${m.category})` : ''}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Selected Material Info */}
      {selectedMaterial && (
        <MaterialPreview material={selectedMaterial} />
      )}
    </div>
  );
}

// ─── Material Preview ───────────────────────────────────────────────────────

function MaterialPreview({ material }: { material: MaterialProfile }) {
  const { properties, slicingDefaults, description } = material;

  return (
    <div className="space-y-3">
      {/* Material Badge */}
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
          {material.name}
        </span>
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
          {material.category}
        </span>
        {material.isBuiltIn && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">
            Built-in
          </span>
        )}
      </div>

      {/* Description */}
      {description && (
        <p className="text-xs text-gray-600">{description}</p>
      )}

      {/* Material Properties */}
      <div className="bg-gray-50 rounded-lg p-3">
        <h4 className="text-xs font-semibold text-gray-700 mb-2">
          Material Properties
        </h4>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <PropRow label="Density" value={`${properties.density} kg/m\u00B3`} />
          {properties.meltTemp !== null && (
            <PropRow label="Melt Temp" value={`${properties.meltTemp}\u00B0C`} />
          )}
          {properties.temperature !== null && (
            <PropRow label="Process Temp" value={`${properties.temperature}\u00B0C`} />
          )}
          <PropRow label="Flow Rate" value={`${properties.flowRate}x`} />
        </div>
      </div>

      {/* Recommended Slicing Parameters */}
      <div className="bg-blue-50 rounded-lg p-3">
        <h4 className="text-xs font-semibold text-blue-800 mb-2">
          Recommended Parameters
        </h4>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <PropRow
            label="Layer Height"
            value={`${slicingDefaults.layerHeight} mm`}
            accent
          />
          <PropRow
            label="Bead Width"
            value={`${slicingDefaults.extrusionWidth} mm`}
            accent
          />
          <PropRow
            label="Walls"
            value={`${slicingDefaults.wallCount}`}
            accent
          />
          <PropRow
            label="Infill"
            value={`${Math.round(slicingDefaults.infillDensity * 100)}%`}
            accent
          />
          <PropRow
            label="Print Speed"
            value={`${slicingDefaults.printSpeed} mm/s`}
            accent
          />
          <PropRow
            label="Travel Speed"
            value={`${slicingDefaults.travelSpeed} mm/s`}
            accent
          />
        </div>

        <p className="text-xs text-blue-600 mt-2 italic">
          These values will auto-fill when you generate a toolpath.
        </p>
      </div>
    </div>
  );
}

function PropRow({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="flex justify-between text-xs">
      <span className={accent ? 'text-blue-700' : 'text-gray-600'}>
        {label}
      </span>
      <span className={`font-medium ${accent ? 'text-blue-900' : 'text-gray-900'}`}>
        {value}
      </span>
    </div>
  );
}
