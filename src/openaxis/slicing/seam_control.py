"""
Seam control for perimeter placement.

DELETED: Custom seam heuristics removed. The previous implementation
had no research citations and used unvalidated normal calculations
for seam shaping.

TODO: Integrate seam placement from compas_slicer's print organization
module, or implement based on cited manufacturing research:
- Ding, D. et al. (2015) "A practical path planning methodology for wire
  and arc additive manufacturing" — seam placement strategies
- ISO/ASTM 52903:2020 — additive manufacturing path planning

Stubs remain for backward compatibility of imports only.
"""

from typing import List, Tuple


def apply_seam(
    contour: List[Tuple[float, float]],
    mode: str = "guided",
    shape: str = "straight",
    layer: int = 0,
    angle_deg: float = 0.0,
    total_layers: int = 100,
) -> List[Tuple[float, float]]:
    """Seam application — not yet implemented with research backing."""
    raise NotImplementedError(
        "Custom seam control deleted due to lack of research citations. "
        "Use compas_slicer's print organization for path ordering, or "
        "implement based on cited manufacturing research."
    )
