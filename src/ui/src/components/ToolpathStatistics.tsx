import {
  ClockIcon,
  CubeIcon,
  ArrowsPointingOutIcon,
  CircleStackIcon,
} from '@heroicons/react/24/outline';

interface ToolpathStatisticsProps {
  statistics: {
    totalSegments: number;
    totalPoints: number;
    layerCount: number;
    estimatedTime: number;  // seconds
    estimatedMaterial: number;  // relative units
  };
  layerHeight: number;
  processType: string;
}

export default function ToolpathStatistics({
  statistics,
  layerHeight,
  processType
}: ToolpathStatisticsProps) {
  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const secs = Math.round(seconds % 60);
      return `${minutes}m ${secs}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${minutes}m`;
    }
  };

  const formatMaterial = (amount: number): string => {
    if (amount < 1000) {
      return `${amount.toFixed(1)} mm`;
    } else if (amount < 1000000) {
      return `${(amount / 1000).toFixed(2)} m`;
    } else {
      return `${(amount / 1000000).toFixed(2)} km`;
    }
  };

  const buildHeight = layerHeight * statistics.layerCount;

  return (
    <div className="bg-white rounded-lg shadow-md p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">Toolpath Statistics</h3>

      {/* Grid of Stats */}
      <div className="grid grid-cols-2 gap-3">
        {/* Layer Count */}
        <div className="flex items-start space-x-3 p-3 bg-blue-50 rounded-lg">
          <div className="flex-shrink-0">
            <CircleStackIcon className="w-5 h-5 text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-600">Layers</p>
            <p className="text-lg font-semibold text-gray-900">
              {statistics.layerCount}
            </p>
          </div>
        </div>

        {/* Build Height */}
        <div className="flex items-start space-x-3 p-3 bg-green-50 rounded-lg">
          <div className="flex-shrink-0">
            <ArrowsPointingOutIcon className="w-5 h-5 text-green-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-600">Height</p>
            <p className="text-lg font-semibold text-gray-900">
              {buildHeight.toFixed(1)}mm
            </p>
          </div>
        </div>

        {/* Estimated Time */}
        <div className="flex items-start space-x-3 p-3 bg-orange-50 rounded-lg">
          <div className="flex-shrink-0">
            <ClockIcon className="w-5 h-5 text-orange-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-600">Est. Time</p>
            <p className="text-lg font-semibold text-gray-900">
              {formatTime(statistics.estimatedTime)}
            </p>
          </div>
        </div>

        {/* Material Usage */}
        <div className="flex items-start space-x-3 p-3 bg-purple-50 rounded-lg">
          <div className="flex-shrink-0">
            <CubeIcon className="w-5 h-5 text-purple-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-600">Material</p>
            <p className="text-lg font-semibold text-gray-900">
              {formatMaterial(statistics.estimatedMaterial)}
            </p>
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="pt-3 border-t border-gray-200 space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-gray-600">Total Segments:</span>
          <span className="font-medium text-gray-900">
            {statistics.totalSegments.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-gray-600">Total Points:</span>
          <span className="font-medium text-gray-900">
            {statistics.totalPoints.toLocaleString()}
          </span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-gray-600">Layer Height:</span>
          <span className="font-medium text-gray-900">{layerHeight}mm</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-gray-600">Process Type:</span>
          <span className="font-medium text-gray-900 uppercase">
            {processType.replace('_', ' ')}
          </span>
        </div>
      </div>

      {/* Average Speed Calculation */}
      {statistics.estimatedTime > 0 && statistics.estimatedMaterial > 0 && (
        <div className="pt-3 border-t border-gray-200">
          <div className="flex justify-between text-xs">
            <span className="text-gray-600">Avg. Speed:</span>
            <span className="font-medium text-gray-900">
              {(statistics.estimatedMaterial / statistics.estimatedTime * 60).toFixed(1)} mm/min
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
