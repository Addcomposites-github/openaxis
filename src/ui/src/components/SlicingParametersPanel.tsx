import React from 'react';

export interface SlicingParameters {
  layerHeight: number;  // mm
  extrusionWidth: number;  // mm
  wallCount: number;
  infillDensity: number;  // 0-1
  infillPattern: 'lines' | 'grid' | 'triangles' | 'hexagons';
  processType: 'waam' | 'pellet_extrusion' | 'milling';
}

interface SlicingParametersPanelProps {
  parameters: SlicingParameters;
  onChange: (parameters: SlicingParameters) => void;
}

export default function SlicingParametersPanel({
  parameters,
  onChange
}: SlicingParametersPanelProps) {
  const handleChange = (key: keyof SlicingParameters, value: any) => {
    onChange({ ...parameters, [key]: value });
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Slicing Parameters
        </h3>
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
          max="5"
          step="0.1"
          value={parameters.layerHeight}
          onChange={(e) => handleChange('layerHeight', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>0.5mm</span>
          <span>5mm</span>
        </div>
      </div>

      {/* Extrusion Width */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-gray-700">
            Extrusion Width
          </label>
          <span className="text-xs text-gray-500">{parameters.extrusionWidth}mm</span>
        </div>
        <input
          type="range"
          min="2"
          max="10"
          step="0.5"
          value={parameters.extrusionWidth}
          onChange={(e) => handleChange('extrusionWidth', parseFloat(e.target.value))}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>2mm</span>
          <span>10mm</span>
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
          <option value="lines">Lines</option>
          <option value="grid">Grid</option>
          <option value="triangles">Triangles</option>
          <option value="hexagons">Hexagons</option>
        </select>
      </div>

      {/* Process Type */}
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Process Type
        </label>
        <select
          value={parameters.processType}
          onChange={(e) => handleChange('processType', e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="waam">WAAM (Wire Arc)</option>
          <option value="pellet_extrusion">Pellet Extrusion</option>
          <option value="milling">Milling</option>
        </select>
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
