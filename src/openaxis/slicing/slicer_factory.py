"""
Factory for instantiating slicers by strategy name.

Provides a registry of available slicing strategies and a convenience
function to create the appropriate slicer instance from a string key
and keyword arguments.
"""

import logging
from typing import Any, Dict, Type, Union

from openaxis.slicing.planar_slicer import PlanarSlicer
from openaxis.slicing.angled_slicer import AngledSlicer
from openaxis.slicing.radial_slicer import RadialSlicer
from openaxis.slicing.curve_slicer import CurveSlicer
from openaxis.slicing.revolved_slicer import RevolvedSlicer

logger = logging.getLogger(__name__)

# Strategy name -> slicer class mapping
SLICER_REGISTRY: Dict[str, Type] = {
    "planar": PlanarSlicer,
    "angled": AngledSlicer,
    "radial": RadialSlicer,
    "curve": CurveSlicer,
    "revolved": RevolvedSlicer,
}


def get_slicer(strategy: str, **kwargs: Any) -> Union[
    PlanarSlicer, AngledSlicer, RadialSlicer, CurveSlicer, RevolvedSlicer
]:
    """
    Create a slicer instance for the given strategy.

    Args:
        strategy: Name of the slicing strategy.  Must be one of the keys
            in ``SLICER_REGISTRY`` ('planar', 'angled', 'radial', 'curve',
            'revolved').
        **kwargs: Keyword arguments forwarded to the slicer constructor.

    Returns:
        An instance of the requested slicer class.

    Raises:
        ValueError: If *strategy* is not found in the registry.

    Examples:
        >>> slicer = get_slicer("planar", layer_height=0.5)
        >>> slicer = get_slicer("angled", slice_angle=30, layer_height=1.0)
        >>> slicer = get_slicer("radial", radius_start=10, radius_end=60)
    """
    strategy_lower = strategy.strip().lower()

    if strategy_lower not in SLICER_REGISTRY:
        available = ", ".join(sorted(SLICER_REGISTRY.keys()))
        raise ValueError(
            f"Unknown slicing strategy '{strategy}'. "
            f"Available strategies: {available}"
        )

    slicer_cls = SLICER_REGISTRY[strategy_lower]
    logger.info("Creating slicer: strategy='%s', class=%s", strategy_lower, slicer_cls.__name__)

    return slicer_cls(**kwargs)
