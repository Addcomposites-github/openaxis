/**
 * SceneHierarchy — Tree view of robot cell, work frames, and geometry parts.
 *
 * Provides a hierarchical scene tree with:
 * - Robot Cell (root)
 *   - Robot (model name)
 *   - Work Frames
 *     - Frame N → assigned parts
 *   - Unassigned Parts
 * - Visibility toggles
 * - Selection on click
 * - Context menu (delete, rename stub)
 * - Search/filter
 */

import { useState, useMemo } from 'react';
import {
  ChevronDownIcon,
  ChevronRightIcon,
  EyeIcon,
  EyeSlashIcon,
  CubeIcon,
  CpuChipIcon,
  Square3Stack3DIcon,
  MagnifyingGlassIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { useWorkspaceStore } from '../stores/workspaceStore';

// ─── Types ───────────────────────────────────────────────────────────────────

interface TreeNode {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  type: 'root' | 'robot' | 'frame' | 'part' | 'group';
  children?: TreeNode[];
  data?: any;
  visible?: boolean;
}

// ─── TreeItem Component ──────────────────────────────────────────────────────

function TreeItem({
  node,
  depth,
  selectedId,
  onSelect,
  onToggleVisibility,
  onDelete,
}: {
  node: TreeNode;
  depth: number;
  selectedId: string | null;
  onSelect: (id: string, type: string) => void;
  onToggleVisibility?: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedId === node.id;
  const Icon = node.icon;

  return (
    <div>
      <div
        className={`flex items-center gap-1 px-2 py-1 cursor-pointer transition-colors rounded-sm ${
          isSelected
            ? 'bg-blue-100 text-blue-900'
            : 'hover:bg-gray-100 text-gray-700'
        }`}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
        onClick={() => {
          if (node.type === 'part') {
            onSelect(node.id, node.type);
          }
          if (hasChildren) {
            setExpanded(!expanded);
          }
        }}
      >
        {/* Expand/collapse arrow */}
        <span className="w-4 h-4 flex items-center justify-center flex-shrink-0">
          {hasChildren ? (
            expanded ? (
              <ChevronDownIcon className="w-3 h-3 text-gray-400" />
            ) : (
              <ChevronRightIcon className="w-3 h-3 text-gray-400" />
            )
          ) : (
            <span className="w-3" />
          )}
        </span>

        {/* Icon */}
        <Icon className={`w-4 h-4 flex-shrink-0 ${isSelected ? 'text-blue-600' : 'text-gray-400'}`} />

        {/* Label */}
        <span className="text-xs flex-1 truncate">{node.label}</span>

        {/* Visibility toggle (parts only) */}
        {node.type === 'part' && onToggleVisibility && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggleVisibility(node.id);
            }}
            className="p-0.5 hover:bg-gray-200 rounded"
          >
            {node.visible !== false ? (
              <EyeIcon className="w-3 h-3 text-gray-400" />
            ) : (
              <EyeSlashIcon className="w-3 h-3 text-gray-300" />
            )}
          </button>
        )}

        {/* Delete button (parts only) */}
        {node.type === 'part' && onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(node.id);
            }}
            className="p-0.5 hover:bg-red-100 rounded opacity-0 group-hover:opacity-100"
          >
            <TrashIcon className="w-3 h-3 text-red-400" />
          </button>
        )}
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div>
          {node.children!.map((child) => (
            <TreeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              onToggleVisibility={onToggleVisibility}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── SceneHierarchy Component ────────────────────────────────────────────────

export default function SceneHierarchy() {
  const parts = useWorkspaceStore((s) => s.geometryParts);
  const selectedPartId = useWorkspaceStore((s) => s.selectedPartId);
  const cellSetup = useWorkspaceStore((s) => s.cellSetup);
  const setSelectedPartId = useWorkspaceStore((s) => s.setSelectedPartId);
  const updateGeometryPart = useWorkspaceStore((s) => s.updateGeometryPart);
  const removeGeometryPart = useWorkspaceStore((s) => s.removeGeometryPart);

  const [searchFilter, setSearchFilter] = useState('');

  // Build tree structure
  const tree = useMemo((): TreeNode => {
    const partNodes: TreeNode[] = parts
      .filter((p) => !searchFilter || p.name.toLowerCase().includes(searchFilter.toLowerCase()))
      .map((p) => ({
        id: p.id,
        label: p.name,
        icon: CubeIcon,
        type: 'part' as const,
        visible: p.visible,
        data: p,
      }));

    const robotLabel = cellSetup.robot.model.replace(/_/g, ' ').toUpperCase();

    return {
      id: 'root',
      label: 'Robot Cell',
      icon: CpuChipIcon,
      type: 'root',
      children: [
        {
          id: 'robot',
          label: robotLabel,
          icon: CpuChipIcon,
          type: 'robot',
        },
        {
          id: 'geometry',
          label: `Geometry (${partNodes.length})`,
          icon: Square3Stack3DIcon,
          type: 'group',
          children: partNodes,
        },
      ],
    };
  }, [parts, cellSetup, searchFilter]);

  const handleSelect = (id: string, type: string) => {
    if (type === 'part') {
      setSelectedPartId(id === selectedPartId ? null : id);
    }
  };

  const handleToggleVisibility = (id: string) => {
    const part = parts.find((p) => p.id === id);
    if (part) {
      updateGeometryPart(id, { visible: !part.visible });
    }
  };

  const handleDelete = (id: string) => {
    removeGeometryPart(id);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Search */}
      <div className="p-2 border-b border-gray-200">
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Filter..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="w-full pl-7 pr-2 py-1 text-xs border border-gray-200 rounded-md focus:border-blue-400 focus:outline-none"
          />
        </div>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-auto py-1">
        <TreeItem
          node={tree}
          depth={0}
          selectedId={selectedPartId}
          onSelect={handleSelect}
          onToggleVisibility={handleToggleVisibility}
          onDelete={handleDelete}
        />
      </div>

      {/* Footer info */}
      <div className="px-3 py-1.5 border-t border-gray-200 bg-gray-50">
        <span className="text-xs text-gray-500">
          {parts.length} part{parts.length !== 1 ? 's' : ''} in scene
        </span>
      </div>
    </div>
  );
}
