import { useEffect, useRef } from 'react';
import { useMaterialStore } from '../stores/materialStore';

export interface SlicingParameters {
  layerHeight: number;  // mm
  extrusionWidth: number;  // mm
  wallCount: number;
  infillDensity: number;  // 0-1
  infillPattern: 'grid' | 'triangles' | 'triangle_grid' | 'radial' | 'offset' | 'hexgrid' | 'medial' | 'zigzag';
  processType: 'waam' | 'pellet_extrusion' | 'milling';
}

/** Clamp a slicing parameter to its valid range. */
function clampSlicingParam(key: keyof SlicingParameters, value: any): any {
  switch (key) {
    case 'layerHeight':
      return Math.max(0.1, Math.min(20, Number(value) || 0.1));
    case 'extrusionWidth':
      return Math.max(0.5, Math.min(40, Number(value) || 0.5));
    case 'wallCount':
      return Math.max(1, Math.min(10, Math.round(Number(value) || 1)));
    case 'infillDensity':
      return Math.max(0, Math.min(1, Number(value) || 0));
    default:
      return value;
  }
}

interface SlicingParametersPanelProps {
  parameters: SlicingParameters;
  onChange: (parameters: SlicingParameters) => void;
}

export default function SlicingParametersPanel({
  parameters,
  onChange
}: SlicingParametersPanelProps) {
  const selectedMaterialId = useMaterialStore((s) => s.selectedMaterialId);
  const materials = useMaterialStore((s) => s.materials);
  const prevMaterialRef = useRef<string | null>(null);

  // When selected material changes, apply its defaults
  useEffect(() => {
    if (selectedMaterialId && selectedMaterialId !== prevMaterialRef.current) {
      const material = materials.find((m) => m.id === selectedMaterialId);
      if (material) {
        const { slicingDefaults } = material;
        onChange({
          layerHeight: slicingDefaults.layerHeight,
          extrusionWidth: slicingDefaults.extrusionWidth,
          wallCount: slicingDefaults.wallCount,
          infillDensity: slicingDefaults.infillDensity,
          infillPattern: slicingDefaults.infillPattern as SlicingParameters['infillPattern'],
          processType: material.processType as SlicingParameters['processType'],
        });
      }
      prevMaterialRef.current = selectedMaterialId;
    }
  }, [selectedMaterialId, materials, onChange]);

  const handleChange = (key: keyof SlicingParameters, value: any) => {
    // Clamp numeric values to valid ranges
    const clamped = clampSlicingParam(key, value);
    onChange({ ...parameters, [key]: clamped });
  };

  // Find currently selected material for badge
  const selectedMaterial = selectedMaterialId
    ? materials.find((m) => m.id === selectedMaterialId)
    : null;

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">
            Slicing Parameters
          </h3>
          {selectedMaterial && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {selectedMaterial.name}
            </span>
          )}
        </div>
        {selectedMaterial && (
          <p className="text-xs text-blue-600 mb-2">
            Parameters auto-filled from material profile. You can override any value below.
          </p>
        )}
      </div>

      {/* Layer Height */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-gray-700">
            Layer Height
          </label>
          <span className="text-xs text-gray-500">{parameters.layerHeight}mm</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="20"
          step="0.1"
          value={parameters.layerHeight}
          onChange={(e) => handleChange('layerHeight', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>0.5mm</span>
          <span>20mm</span>
        </div>
      </div>

      {/* Extrusion Width */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-gray-700">
            Bead / Extrusion Width
          </label>
          <span className="text-xs text-gray-500">{parameters.extrusionWidth}mm</span>
        </div>
        <input
          type="range"
          min="1"
          max="40"
          step="0.5"
          value={parameters.extrusionWidth}
          onChange={(e) => handleChange('extrusionWidth', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>1mm</span>
          <span>40mm</span>
        </div>
      </div>

      {/* Wall Count */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-gray-700">
            Walls (Perimeters)
          </label>
          <span className="text-xs text-gray-500">{parameters.wallCount}</span>
        </div>
        <input
          type="range"
          min="1"
          max="5"
          step="1"
          value={parameters.wallCount}
          onChange={(e) => handleChange('wallCount', parseInt(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>1</span>
          <span>5</span>
        </div>
      </div>

      {/* Infill Density */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-gray-700">
            Infill Density
          </label>
          <span className="text-xs text-gray-500">{Math.round(parameters.infillDensity * 100)}%</span>
        </div>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={parameters.infillDensity}
          onChange={(e) => handleChange('infillDensity', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>0%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Infill Pattern */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Infill Pattern
        </label>
        <select
          value={parameters.infillPattern}
          onChange={(e) => handleChange('infillPattern', e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="grid">Grid (0/90 alternating)</option>
          <option value="triangles">Triangles (60 rotation)</option>
          <option value="triangle_grid">Triangle Grid (dense)</option>
          <option value="radial">Radial (concentric circles)</option>
          <option value="offset">Offset (concentric contours)</option>
          <option value="hexgrid">Hexagonal Honeycomb</option>
          <option value="medial">Medial Axis</option>
          <option value="zigzag">Zigzag (continuous)</option>
        </select>
      </div>

      {/* Process Type (read-only — set in Setup > Process tab) */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Process Type
        </label>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 text-gray-800 border border-gray-200">
            {parameters.processType === 'waam' ? 'WAAM (Wire Arc)' :
             parameters.processType === 'pellet_extrusion' ? 'Pellet Extrusion' :
             parameters.processType === 'milling' ? 'Milling' :
             parameters.processType}
          </span>
          <span className="text-xs text-gray-400">Set in Setup → Process</span>
        </div>
      </div>

      {/* Summary */}
      <div className="pt-3 border-t border-gray-200">
        <div className="text-xs text-gray-600 space-y-1">
          <div className="flex justify-between">
            <span>Estimated Layers:</span>
            <span className="font-medium">~{Math.ceil(50 / parameters.layerHeight)}</span>
          </div>
          <div className="flex justify-between">
            <span>Est. Print Time:</span>
            <span className="font-medium">~{Math.ceil(50 / parameters.layerHeight * 0.5)} min</span>
          </div>
        </div>
      </div>
    </div>
  );
}
