"""
OpenAxis Post Processor Module

Provides multi-format export for toolpath data:
- ABB RAPID (.mod)
- KUKA KRL (.src)
- Fanuc LS (.ls)
- Configurable G-code (.gcode / .nc)

Each post processor inherits from PostProcessorBase and implements
vendor-specific code generation with event hooks for customization.
"""

from .base import PostProcessorBase, PostProcessorConfig, EventHooks
from .rapid import RAPIDPostProcessor
from .krl import KRLPostProcessor
from .fanuc import FanucPostProcessor
from .gcode_configurable import GCodePostProcessor

__all__ = [
    'PostProcessorBase',
    'PostProcessorConfig',
    'EventHooks',
    'RAPIDPostProcessor',
    'KRLPostProcessor',
    'FanucPostProcessor',
    'GCodePostProcessor',
]
