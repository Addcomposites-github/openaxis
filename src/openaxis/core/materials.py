"""
Material library for OpenAxis.

Provides dataclasses for material profiles and a library that manages
built-in + custom material profiles. Each profile contains recommended
slicing/process parameters for a specific material + process combination.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
import json
import os
from pathlib import Path

from openaxis.core.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class MaterialProperties:
    """Physical and process properties of a material."""
    density: float = 7850.0         # kg/m3
    melt_temp: Optional[float] = None  # C
    bead_width: float = 5.0         # mm (recommended)
    layer_height: float = 2.0       # mm (recommended)
    print_speed: float = 10.0       # mm/s
    travel_speed: float = 50.0      # mm/s
    temperature: Optional[float] = None  # C (nozzle/arc)
    flow_rate: float = 1.0          # multiplier


@dataclass
class SlicingDefaults:
    """Default slicing parameters for a material profile."""
    layer_height: float = 2.0       # mm
    extrusion_width: float = 5.0    # mm
    wall_count: int = 1
    infill_density: float = 0.2     # 0-1
    infill_pattern: str = 'lines'
    print_speed: float = 10.0       # mm/s
    travel_speed: float = 50.0      # mm/s


@dataclass
class MaterialProfile:
    """A complete material profile with process parameters."""
    id: str
    name: str
    process_type: str               # waam, pellet_extrusion, milling, wire_laser, concrete
    category: str                   # metal, polymer, concrete, composite
    properties: MaterialProperties = field(default_factory=MaterialProperties)
    slicing_defaults: SlicingDefaults = field(default_factory=SlicingDefaults)
    is_built_in: bool = True
    description: str = ''

    def to_dict(self) -> dict:
        """Serialize to dict for JSON/API."""
        return {
            'id': self.id,
            'name': self.name,
            'processType': self.process_type,
            'category': self.category,
            'description': self.description,
            'isBuiltIn': self.is_built_in,
            'properties': {
                'density': self.properties.density,
                'meltTemp': self.properties.melt_temp,
                'beadWidth': self.properties.bead_width,
                'layerHeight': self.properties.layer_height,
                'printSpeed': self.properties.print_speed,
                'travelSpeed': self.properties.travel_speed,
                'temperature': self.properties.temperature,
                'flowRate': self.properties.flow_rate,
            },
            'slicingDefaults': {
                'layerHeight': self.slicing_defaults.layer_height,
                'extrusionWidth': self.slicing_defaults.extrusion_width,
                'wallCount': self.slicing_defaults.wall_count,
                'infillDensity': self.slicing_defaults.infill_density,
                'infillPattern': self.slicing_defaults.infill_pattern,
                'printSpeed': self.slicing_defaults.print_speed,
                'travelSpeed': self.slicing_defaults.travel_speed,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MaterialProfile':
        """Deserialize from dict."""
        props = data.get('properties', {})
        slicing = data.get('slicingDefaults', {})
        return cls(
            id=data['id'],
            name=data['name'],
            process_type=data.get('processType', 'waam'),
            category=data.get('category', 'metal'),
            description=data.get('description', ''),
            is_built_in=data.get('isBuiltIn', False),
            properties=MaterialProperties(
                density=props.get('density', 7850.0),
                melt_temp=props.get('meltTemp'),
                bead_width=props.get('beadWidth', 5.0),
                layer_height=props.get('layerHeight', 2.0),
                print_speed=props.get('printSpeed', 10.0),
                travel_speed=props.get('travelSpeed', 50.0),
                temperature=props.get('temperature'),
                flow_rate=props.get('flowRate', 1.0),
            ),
            slicing_defaults=SlicingDefaults(
                layer_height=slicing.get('layerHeight', 2.0),
                extrusion_width=slicing.get('extrusionWidth', 5.0),
                wall_count=slicing.get('wallCount', 1),
                infill_density=slicing.get('infillDensity', 0.2),
                infill_pattern=slicing.get('infillPattern', 'lines'),
                print_speed=slicing.get('printSpeed', 10.0),
                travel_speed=slicing.get('travelSpeed', 50.0),
            ),
        )


# ─── Built-in Material Profiles ───────────────────────────────────────────────

BUILT_IN_MATERIALS: List[MaterialProfile] = [
    # ─── WAAM Materials ───
    MaterialProfile(
        id='waam_steel_er70s6',
        name='Steel ER70S-6',
        process_type='waam',
        category='metal',
        description='Low-carbon steel welding wire. Most common WAAM material for structural components.',
        properties=MaterialProperties(
            density=7850.0,
            melt_temp=1500.0,
            bead_width=5.0,
            layer_height=2.0,
            print_speed=10.0,
            travel_speed=80.0,
            temperature=None,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=2.0,
            extrusion_width=5.0,
            wall_count=1,
            infill_density=1.0,
            infill_pattern='lines',
            print_speed=10.0,
            travel_speed=80.0,
        ),
    ),
    MaterialProfile(
        id='waam_stainless_316l',
        name='Stainless Steel 316L',
        process_type='waam',
        category='metal',
        description='Austenitic stainless steel. Corrosion-resistant, used for marine/chemical/food applications.',
        properties=MaterialProperties(
            density=7990.0,
            melt_temp=1400.0,
            bead_width=4.5,
            layer_height=1.8,
            print_speed=8.0,
            travel_speed=70.0,
            temperature=None,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=1.8,
            extrusion_width=4.5,
            wall_count=1,
            infill_density=1.0,
            infill_pattern='lines',
            print_speed=8.0,
            travel_speed=70.0,
        ),
    ),
    MaterialProfile(
        id='waam_aluminum_5356',
        name='Aluminum 5356',
        process_type='waam',
        category='metal',
        description='Aluminum-magnesium alloy wire. Lightweight structures, aerospace applications.',
        properties=MaterialProperties(
            density=2640.0,
            melt_temp=660.0,
            bead_width=6.0,
            layer_height=2.5,
            print_speed=12.0,
            travel_speed=100.0,
            temperature=None,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=2.5,
            extrusion_width=6.0,
            wall_count=1,
            infill_density=1.0,
            infill_pattern='lines',
            print_speed=12.0,
            travel_speed=100.0,
        ),
    ),
    MaterialProfile(
        id='waam_titanium_ti64',
        name='Titanium Ti-6Al-4V',
        process_type='waam',
        category='metal',
        description='Titanium alloy. Aerospace, medical implants. Requires inert atmosphere.',
        properties=MaterialProperties(
            density=4430.0,
            melt_temp=1668.0,
            bead_width=4.0,
            layer_height=1.5,
            print_speed=6.0,
            travel_speed=60.0,
            temperature=None,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=1.5,
            extrusion_width=4.0,
            wall_count=1,
            infill_density=1.0,
            infill_pattern='lines',
            print_speed=6.0,
            travel_speed=60.0,
        ),
    ),

    # ─── Pellet Extrusion Materials ───
    MaterialProfile(
        id='pellet_pla',
        name='PLA Pellets',
        process_type='pellet_extrusion',
        category='polymer',
        description='Polylactic acid pellets. Biodegradable, easy to print, good for prototyping.',
        properties=MaterialProperties(
            density=1240.0,
            melt_temp=180.0,
            bead_width=8.0,
            layer_height=3.0,
            print_speed=30.0,
            travel_speed=100.0,
            temperature=200.0,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=3.0,
            extrusion_width=8.0,
            wall_count=2,
            infill_density=0.2,
            infill_pattern='lines',
            print_speed=30.0,
            travel_speed=100.0,
        ),
    ),
    MaterialProfile(
        id='pellet_petg',
        name='PETG Pellets',
        process_type='pellet_extrusion',
        category='polymer',
        description='Polyethylene terephthalate glycol. Good chemical resistance, impact strength.',
        properties=MaterialProperties(
            density=1270.0,
            melt_temp=230.0,
            bead_width=8.0,
            layer_height=3.0,
            print_speed=25.0,
            travel_speed=90.0,
            temperature=240.0,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=3.0,
            extrusion_width=8.0,
            wall_count=2,
            infill_density=0.2,
            infill_pattern='grid',
            print_speed=25.0,
            travel_speed=90.0,
        ),
    ),
    MaterialProfile(
        id='pellet_abs',
        name='ABS Pellets',
        process_type='pellet_extrusion',
        category='polymer',
        description='Acrylonitrile butadiene styrene. Durable, heat-resistant, industrial parts.',
        properties=MaterialProperties(
            density=1040.0,
            melt_temp=230.0,
            bead_width=8.0,
            layer_height=3.0,
            print_speed=25.0,
            travel_speed=90.0,
            temperature=250.0,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=3.0,
            extrusion_width=8.0,
            wall_count=2,
            infill_density=0.2,
            infill_pattern='lines',
            print_speed=25.0,
            travel_speed=90.0,
        ),
    ),
    MaterialProfile(
        id='pellet_cf_pa',
        name='Carbon Fiber PA (Nylon)',
        process_type='pellet_extrusion',
        category='composite',
        description='Carbon fiber reinforced polyamide. High strength-to-weight, tooling/molds.',
        properties=MaterialProperties(
            density=1200.0,
            melt_temp=260.0,
            bead_width=10.0,
            layer_height=3.5,
            print_speed=20.0,
            travel_speed=80.0,
            temperature=280.0,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=3.5,
            extrusion_width=10.0,
            wall_count=2,
            infill_density=0.3,
            infill_pattern='lines',
            print_speed=20.0,
            travel_speed=80.0,
        ),
    ),

    # ─── Wire Laser Materials ───
    MaterialProfile(
        id='wire_laser_steel_316l',
        name='Steel 316L Wire',
        process_type='wire_laser',
        category='metal',
        description='Stainless steel wire for laser DED. High precision, part repair applications.',
        properties=MaterialProperties(
            density=7990.0,
            melt_temp=1400.0,
            bead_width=1.5,
            layer_height=0.7,
            print_speed=8.0,
            travel_speed=50.0,
            temperature=None,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=0.7,
            extrusion_width=1.5,
            wall_count=1,
            infill_density=1.0,
            infill_pattern='lines',
            print_speed=8.0,
            travel_speed=50.0,
        ),
    ),

    # ─── Concrete ───
    MaterialProfile(
        id='concrete_standard',
        name='Standard Concrete Mix',
        process_type='concrete',
        category='concrete',
        description='Standard printable concrete. Large-scale construction, walls, structures.',
        properties=MaterialProperties(
            density=2300.0,
            melt_temp=None,
            bead_width=30.0,
            layer_height=15.0,
            print_speed=50.0,
            travel_speed=100.0,
            temperature=None,
            flow_rate=1.0,
        ),
        slicing_defaults=SlicingDefaults(
            layer_height=15.0,
            extrusion_width=30.0,
            wall_count=2,
            infill_density=0.0,
            infill_pattern='lines',
            print_speed=50.0,
            travel_speed=100.0,
        ),
    ),
]


class MaterialLibrary:
    """Manages built-in and custom material profiles."""

    def __init__(self, custom_dir: Optional[str] = None):
        self._materials: Dict[str, MaterialProfile] = {}
        self._custom_dir = custom_dir

        # Load built-in materials
        for mat in BUILT_IN_MATERIALS:
            self._materials[mat.id] = mat

        # Load custom materials from directory
        if custom_dir and os.path.isdir(custom_dir):
            self._load_custom_materials(custom_dir)

    def _load_custom_materials(self, directory: str) -> None:
        """Load custom material profiles from JSON files."""
        for file in Path(directory).glob('*.json'):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        mat = MaterialProfile.from_dict(item)
                        mat.is_built_in = False
                        self._materials[mat.id] = mat
                else:
                    mat = MaterialProfile.from_dict(data)
                    mat.is_built_in = False
                    self._materials[mat.id] = mat
            except Exception as e:
                _logger.warning("material_load_failed", file=str(file), error=str(e))

    def get_all(self) -> List[MaterialProfile]:
        """Get all material profiles."""
        return list(self._materials.values())

    def get_by_id(self, material_id: str) -> Optional[MaterialProfile]:
        """Get a material profile by ID."""
        return self._materials.get(material_id)

    def get_by_process(self, process_type: str) -> List[MaterialProfile]:
        """Get all materials for a given process type."""
        return [m for m in self._materials.values() if m.process_type == process_type]

    def get_by_category(self, category: str) -> List[MaterialProfile]:
        """Get all materials in a category."""
        return [m for m in self._materials.values() if m.category == category]

    def add_custom(self, profile: MaterialProfile) -> None:
        """Add a custom material profile."""
        profile.is_built_in = False
        self._materials[profile.id] = profile

        # Save to custom directory if configured
        if self._custom_dir:
            os.makedirs(self._custom_dir, exist_ok=True)
            file_path = os.path.join(self._custom_dir, f"{profile.id}.json")
            with open(file_path, 'w') as f:
                json.dump(profile.to_dict(), f, indent=2)

    def remove_custom(self, material_id: str) -> bool:
        """Remove a custom material (built-in materials cannot be removed)."""
        mat = self._materials.get(material_id)
        if mat and not mat.is_built_in:
            del self._materials[material_id]
            # Remove file if exists
            if self._custom_dir:
                file_path = os.path.join(self._custom_dir, f"{material_id}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
            return True
        return False

    def get_process_types(self) -> List[str]:
        """Get list of unique process types."""
        return sorted(set(m.process_type for m in self._materials.values()))

    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        return sorted(set(m.category for m in self._materials.values()))
