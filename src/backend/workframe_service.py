"""
Work frame service for OpenAxis backend.

Manages work frames (coordinate systems) — alignment computations,
coordinate transforms between frames, and CRUD operations.
"""

import math
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class WorkFrameData:
    """Work frame definition."""
    id: str
    name: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)   # mm, world
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)    # euler degrees
    size: Tuple[float, float, float] = (1.0, 0.05, 1.0)       # meters (scene)
    alignment_method: str = 'manual'
    child_part_ids: List[str] = field(default_factory=list)
    is_default: bool = False
    visible: bool = True
    color: str = '#3b82f6'

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'position': list(self.position),
            'rotation': list(self.rotation),
            'size': list(self.size),
            'alignmentMethod': self.alignment_method,
            'childPartIds': self.child_part_ids,
            'isDefault': self.is_default,
            'visible': self.visible,
            'color': self.color,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorkFrameData':
        return cls(
            id=data['id'],
            name=data['name'],
            position=tuple(data.get('position', [0, 0, 0])),
            rotation=tuple(data.get('rotation', [0, 0, 0])),
            size=tuple(data.get('size', [1.0, 0.05, 1.0])),
            alignment_method=data.get('alignmentMethod', 'manual'),
            child_part_ids=data.get('childPartIds', []),
            is_default=data.get('isDefault', False),
            visible=data.get('visible', True),
            color=data.get('color', '#3b82f6'),
        )


class WorkFrameService:
    """Service for work frame management and coordinate transforms."""

    def __init__(self) -> None:
        self._frames: Dict[str, WorkFrameData] = {}
        # Create default frame
        default = WorkFrameData(
            id='default_workframe',
            name='Build Platform',
            position=(2000, 0, 0),
            rotation=(0, 0, 0),
            size=(1.5, 0.05, 1.5),
            is_default=True,
        )
        self._frames[default.id] = default

    # ── CRUD ──────────────────────────────────────────────────────────────

    def get_all_frames(self) -> List[dict]:
        """Get all work frames."""
        return [f.to_dict() for f in self._frames.values()]

    def get_frame(self, frame_id: str) -> Optional[dict]:
        """Get a single frame by ID."""
        f = self._frames.get(frame_id)
        return f.to_dict() if f else None

    def create_frame(self, data: dict) -> dict:
        """Create a new work frame."""
        frame = WorkFrameData.from_dict(data)
        frame.is_default = False  # Only the initial one is default
        self._frames[frame.id] = frame
        return frame.to_dict()

    def update_frame(self, frame_id: str, updates: dict) -> Optional[dict]:
        """Update a work frame."""
        frame = self._frames.get(frame_id)
        if not frame:
            return None

        if 'name' in updates:
            frame.name = updates['name']
        if 'position' in updates:
            frame.position = tuple(updates['position'])
        if 'rotation' in updates:
            frame.rotation = tuple(updates['rotation'])
        if 'size' in updates:
            frame.size = tuple(updates['size'])
        if 'alignmentMethod' in updates:
            frame.alignment_method = updates['alignmentMethod']
        if 'visible' in updates:
            frame.visible = updates['visible']
        if 'color' in updates:
            frame.color = updates['color']
        if 'childPartIds' in updates:
            frame.child_part_ids = updates['childPartIds']

        return frame.to_dict()

    def delete_frame(self, frame_id: str) -> bool:
        """Delete a work frame. Cannot delete default frame."""
        frame = self._frames.get(frame_id)
        if not frame or frame.is_default:
            return False

        # Move orphaned parts to default frame
        default = next((f for f in self._frames.values() if f.is_default), None)
        if default and frame.child_part_ids:
            default.child_part_ids.extend(frame.child_part_ids)

        del self._frames[frame_id]
        return True

    # ── Coordinate Transforms ────────────────────────────────────────────

    def transform_point_to_frame(
        self, point_world: Tuple[float, float, float], frame_id: str
    ) -> Optional[Tuple[float, float, float]]:
        """Transform a point from world coordinates to a frame's local coordinates.

        Both input and output are in mm, Z-up convention.
        """
        frame = self._frames.get(frame_id)
        if not frame:
            return None

        # Translate to frame origin
        px = point_world[0] - frame.position[0]
        py = point_world[1] - frame.position[1]
        pz = point_world[2] - frame.position[2]

        # Apply inverse rotation (euler ZYX convention, in degrees)
        rx = math.radians(-frame.rotation[0])
        ry = math.radians(-frame.rotation[1])
        rz = math.radians(-frame.rotation[2])

        # Rotate around Z (yaw)
        x1 = px * math.cos(rz) + py * math.sin(rz)
        y1 = -px * math.sin(rz) + py * math.cos(rz)
        z1 = pz

        # Rotate around Y (pitch)
        x2 = x1 * math.cos(ry) - z1 * math.sin(ry)
        y2 = y1
        z2 = x1 * math.sin(ry) + z1 * math.cos(ry)

        # Rotate around X (roll)
        x3 = x2
        y3 = y2 * math.cos(rx) + z2 * math.sin(rx)
        z3 = -y2 * math.sin(rx) + z2 * math.cos(rx)

        return (x3, y3, z3)

    def transform_point_from_frame(
        self, point_local: Tuple[float, float, float], frame_id: str
    ) -> Optional[Tuple[float, float, float]]:
        """Transform a point from frame-local coordinates to world coordinates.

        Both input and output are in mm, Z-up convention.
        """
        frame = self._frames.get(frame_id)
        if not frame:
            return None

        rx = math.radians(frame.rotation[0])
        ry = math.radians(frame.rotation[1])
        rz = math.radians(frame.rotation[2])

        px, py, pz = point_local

        # Rotate around X (roll)
        x1 = px
        y1 = py * math.cos(rx) - pz * math.sin(rx)
        z1 = py * math.sin(rx) + pz * math.cos(rx)

        # Rotate around Y (pitch)
        x2 = x1 * math.cos(ry) + z1 * math.sin(ry)
        y2 = y1
        z2 = -x1 * math.sin(ry) + z1 * math.cos(ry)

        # Rotate around Z (yaw)
        x3 = x2 * math.cos(rz) - y2 * math.sin(rz)
        y3 = x2 * math.sin(rz) + y2 * math.cos(rz)
        z3 = z2

        # Translate from frame origin to world
        return (
            x3 + frame.position[0],
            y3 + frame.position[1],
            z3 + frame.position[2],
        )

    def compute_alignment_z_plus_x(
        self,
        origin: Tuple[float, float, float],
        z_point: Tuple[float, float, float],
        x_point: Tuple[float, float, float],
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
        """Compute frame position and rotation from Z+X axis alignment method.

        Given:
        - origin: Frame origin point (mm)
        - z_point: Point defining positive Z direction
        - x_point: Point defining approximate X direction

        Returns (position, rotation_degrees) for the frame.
        """
        # Z axis from origin to z_point
        zx = z_point[0] - origin[0]
        zy = z_point[1] - origin[1]
        zz = z_point[2] - origin[2]
        z_len = math.sqrt(zx * zx + zy * zy + zz * zz)
        if z_len < 1e-6:
            return origin, (0.0, 0.0, 0.0)
        zx, zy, zz = zx / z_len, zy / z_len, zz / z_len

        # Approximate X direction
        xx = x_point[0] - origin[0]
        xy = x_point[1] - origin[1]
        xz = x_point[2] - origin[2]

        # Y = Z cross X (orthogonalize)
        yx = zy * xz - zz * xy
        yy = zz * xx - zx * xz
        yz = zx * xy - zy * xx
        y_len = math.sqrt(yx * yx + yy * yy + yz * yz)
        if y_len < 1e-6:
            return origin, (0.0, 0.0, 0.0)
        yx, yy, yz = yx / y_len, yy / y_len, yz / y_len

        # Recompute X = Y cross Z (ensure orthogonal)
        xx = yy * zz - yz * zy
        xy = yz * zx - yx * zz
        xz = yx * zy - yy * zx

        # Extract Euler angles from rotation matrix (ZYX convention)
        pitch = math.asin(-zx)
        if abs(math.cos(pitch)) > 1e-6:
            roll = math.atan2(zy, zz)
            yaw = math.atan2(yx, xx)
        else:
            roll = 0.0
            yaw = math.atan2(-xy, yy)

        rotation = (
            math.degrees(roll),
            math.degrees(pitch),
            math.degrees(yaw),
        )
        return origin, rotation

    def get_scene_position(self, frame_id: str) -> Optional[Tuple[float, float, float]]:
        """Convert frame position from mm Z-up to meters Y-up for Three.js scene.

        mm Z-up: [x, y, z] → scene Y-up: [x*0.001, z*0.001, -y*0.001]
        """
        frame = self._frames.get(frame_id)
        if not frame:
            return None
        return (
            frame.position[0] * 0.001,
            frame.position[2] * 0.001,
            -frame.position[1] * 0.001,
        )
