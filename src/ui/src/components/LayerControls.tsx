import React, { useState, useEffect } from 'react';
import {
  PlayIcon,
  PauseIcon,
  BackwardIcon,
  ForwardIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';

interface LayerControlsProps {
  totalLayers: number;
  currentLayer: number;
  onLayerChange: (layer: number) => void;
  showAllLayers: boolean;
  onShowAllLayersChange: (showAll: boolean) => void;
}

export default function LayerControls({
  totalLayers,
  currentLayer,
  onLayerChange,
  showAllLayers,
  onShowAllLayersChange
}: LayerControlsProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [playSpeed, setPlaySpeed] = useState(1.0); // layers per second

  // Animation effect
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      onLayerChange((currentLayer + 1) % totalLayers);
    }, 1000 / playSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, currentLayer, totalLayers, playSpeed, onLayerChange]);

  const handlePrevious = () => {
    setIsPlaying(false);
    onLayerChange(Math.max(0, currentLayer - 1));
  };

  const handleNext = () => {
    setIsPlaying(false);
    onLayerChange(Math.min(totalLayers - 1, currentLayer + 1));
  };

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  const handleReset = () => {
    setIsPlaying(false);
    onLayerChange(0);
  };

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIsPlaying(false);
    onLayerChange(parseInt(e.target.value));
  };

  const handleJumpToLayer = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const input = e.currentTarget.elements.namedItem('layerInput') as HTMLInputElement;
    const layer = parseInt(input.value);
    if (!isNaN(layer) && layer >= 0 && layer < totalLayers) {
      setIsPlaying(false);
      onLayerChange(layer);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-4 space-y-4">
      {/* Layer Display */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900">Layer Control</h3>
        <div className="text-sm font-mono">
          <span className="text-blue-600 font-bold">{currentLayer + 1}</span>
          <span className="text-gray-400"> / </span>
          <span className="text-gray-600">{totalLayers}</span>
        </div>
      </div>

      {/* Layer Slider */}
      <div>
        <input
          type="range"
          min="0"
          max={totalLayers - 1}
          value={currentLayer}
          onChange={handleSliderChange}
          disabled={showAllLayers}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>Layer 1</span>
          <span>Layer {totalLayers}</span>
        </div>
      </div>

      {/* Playback Controls */}
      <div className="flex items-center justify-center space-x-2">
        <button
          onClick={handleReset}
          disabled={showAllLayers}
          className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Reset to Layer 1"
        >
          <ArrowPathIcon className="w-4 h-4 text-gray-700" />
        </button>

        <button
          onClick={handlePrevious}
          disabled={showAllLayers || currentLayer === 0}
          className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Previous Layer"
        >
          <BackwardIcon className="w-4 h-4 text-gray-700" />
        </button>

        <button
          onClick={handlePlayPause}
          disabled={showAllLayers}
          className="p-3 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <PauseIcon className="w-5 h-5 text-white" />
          ) : (
            <PlayIcon className="w-5 h-5 text-white" />
          )}
        </button>

        <button
          onClick={handleNext}
          disabled={showAllLayers || currentLayer === totalLayers - 1}
          className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Next Layer"
        >
          <ForwardIcon className="w-4 h-4 text-gray-700" />
        </button>
      </div>

      {/* Speed Control */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-gray-700">
            Animation Speed
          </label>
          <span className="text-xs text-gray-500">{playSpeed.toFixed(1)}x</span>
        </div>
        <input
          type="range"
          min="0.25"
          max="4"
          step="0.25"
          value={playSpeed}
          onChange={(e) => setPlaySpeed(parseFloat(e.target.value))}
          disabled={showAllLayers}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 disabled:opacity-50"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>0.25x</span>
          <span>4x</span>
        </div>
      </div>

      {/* Toggle Show All Layers */}
      <div className="pt-3 border-t border-gray-200">
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showAllLayers}
            onChange={(e) => {
              setIsPlaying(false);
              onShowAllLayersChange(e.target.checked);
            }}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Show All Layers</span>
        </label>
      </div>

      {/* Jump to Layer */}
      <div className="pt-3 border-t border-gray-200">
        <form onSubmit={handleJumpToLayer} className="flex space-x-2">
          <input
            type="number"
            name="layerInput"
            min="1"
            max={totalLayers}
            placeholder="Jump to..."
            disabled={showAllLayers}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={showAllLayers}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Go
          </button>
        </form>
      </div>
    </div>
  );
}
