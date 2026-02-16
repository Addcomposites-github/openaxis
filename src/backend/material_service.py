"""
Material service for OpenAxis backend.

Manages material profiles - both built-in and custom.
Provides CRUD operations exposed via FastAPI endpoints.
"""

import os
from typing import List, Optional, Dict
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from openaxis.core.materials import MaterialLibrary, MaterialProfile


class MaterialService:
    """Service for managing material profiles."""

    def __init__(self, custom_materials_dir: Optional[str] = None):
        if custom_materials_dir is None:
            # Default: config/materials relative to project root
            project_root = Path(__file__).parent.parent.parent
            custom_materials_dir = str(project_root / 'config' / 'materials')

        self.library = MaterialLibrary(custom_dir=custom_materials_dir)

    def get_all_materials(self) -> List[dict]:
        """Get all materials as serialized dicts."""
        return [m.to_dict() for m in self.library.get_all()]

    def get_material_by_id(self, material_id: str) -> Optional[dict]:
        """Get a single material by ID."""
        mat = self.library.get_by_id(material_id)
        return mat.to_dict() if mat else None

    def get_materials_by_process(self, process_type: str) -> List[dict]:
        """Get materials filtered by process type."""
        return [m.to_dict() for m in self.library.get_by_process(process_type)]

    def get_materials_by_category(self, category: str) -> List[dict]:
        """Get materials filtered by category."""
        return [m.to_dict() for m in self.library.get_by_category(category)]

    def create_custom_material(self, data: dict) -> dict:
        """Create a new custom material profile."""
        profile = MaterialProfile.from_dict(data)
        profile.is_built_in = False
        self.library.add_custom(profile)
        return profile.to_dict()

    def delete_custom_material(self, material_id: str) -> bool:
        """Delete a custom material profile."""
        return self.library.remove_custom(material_id)

    def get_process_types(self) -> List[str]:
        """Get list of available process types."""
        return self.library.get_process_types()

    def get_categories(self) -> List[str]:
        """Get list of available material categories."""
        return self.library.get_categories()

    def get_summary(self) -> Dict:
        """Get a summary of available materials."""
        all_materials = self.library.get_all()
        process_counts = {}
        for m in all_materials:
            process_counts[m.process_type] = process_counts.get(m.process_type, 0) + 1

        return {
            'totalMaterials': len(all_materials),
            'builtIn': sum(1 for m in all_materials if m.is_built_in),
            'custom': sum(1 for m in all_materials if not m.is_built_in),
            'processTypes': self.library.get_process_types(),
            'categories': self.library.get_categories(),
            'materialsPerProcess': process_counts,
        }
