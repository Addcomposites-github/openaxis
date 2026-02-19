"""
Lead-in / lead-out / retract moves for contour starts and ends.

DELETED: Custom trigonometric lead-in/lead-out code removed.
While the math was standard NC programming (approach angle calculations),
it was not from any cited standard (ISO 6983, NIST RS274NGC) and had
no validation against actual machine behavior.

TODO: Implement based on ISO 6983 G-code standards for approach moves,
or integrate from compas_slicer's print organization module.

Stubs remain for backward compatibility of imports only.
"""

from typing import List, Tuple


def add_engage_disengage(
    points_3d: List[Tuple[float, float, float]],
    lead_in_distance: float = 0.0,
    lead_in_angle: float = 45.0,
    lead_out_distance: float = 0.0,
    lead_out_angle: float = 45.0,
    approach_height: float = 2.0,
) -> List[Tuple[float, float, float]]:
    """Engage/disengage moves — not yet implemented with standard citation."""
    raise NotImplementedError(
        "Custom engage/disengage deleted. Implement based on ISO 6983 "
        "or integrate from compas_slicer print organization."
    )


def add_lead_in(
    points_3d: List[Tuple[float, float, float]],
    distance: float = 2.0,
    angle: float = 45.0,
    approach_height: float = 2.0,
) -> List[Tuple[float, float, float]]:
    """Lead-in move — not yet implemented with standard citation."""
    raise NotImplementedError(
        "Custom lead-in deleted. Implement based on ISO 6983."
    )


def add_lead_out(
    points_3d: List[Tuple[float, float, float]],
    distance: float = 2.0,
    angle: float = 45.0,
    retract_height: float = 2.0,
) -> List[Tuple[float, float, float]]:
    """Lead-out move — not yet implemented with standard citation."""
    raise NotImplementedError(
        "Custom lead-out deleted. Implement based on ISO 6983."
    )
