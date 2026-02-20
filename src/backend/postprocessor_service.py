"""
Post Processor Service — selects and runs the appropriate post processor.

Manages post processor instances and configuration, provides export functionality.
"""

from typing import Any, Dict, List, Optional

from openaxis.core.logging import get_logger

logger = get_logger(__name__)

try:
    from openaxis.postprocessor import (
        PostProcessorBase,
        PostProcessorConfig,
        EventHooks,
        RAPIDPostProcessor,
        KRLPostProcessor,
        FanucPostProcessor,
        GCodePostProcessor,
    )
    POSTPROCESSORS_AVAILABLE = True
except ImportError:
    POSTPROCESSORS_AVAILABLE = False
    logger.warning("Post processor module not available")


# Available format definitions
FORMAT_INFO = {
    'gcode': {
        'name': 'G-code',
        'description': 'Standard G-code for CNC and 3D printing',
        'extension': '.gcode',
        'vendor': 'Generic',
        'extensions': ['.gcode', '.nc', '.ngc'],
    },
    'rapid': {
        'name': 'ABB RAPID',
        'description': 'ABB robot program (.mod) with MoveL/MoveJ',
        'extension': '.mod',
        'vendor': 'ABB',
        'extensions': ['.mod'],
    },
    'krl': {
        'name': 'KUKA KRL',
        'description': 'KUKA robot program (.src) with LIN/PTP',
        'extension': '.src',
        'vendor': 'KUKA',
        'extensions': ['.src'],
    },
    'fanuc': {
        'name': 'Fanuc LS',
        'description': 'Fanuc robot program (.ls) with J/L instructions',
        'extension': '.ls',
        'vendor': 'Fanuc',
        'extensions': ['.ls'],
    },
}


class PostProcessorService:
    """Service for selecting and running post processors."""

    def __init__(self) -> None:
        logger.info("PostProcessorService initialized")

    def get_available_formats(self) -> List[Dict[str, Any]]:
        """Return list of available export formats."""
        formats = []
        for fmt_id, info in FORMAT_INFO.items():
            formats.append({
                'id': fmt_id,
                **info,
                'available': POSTPROCESSORS_AVAILABLE,
            })
        return formats

    def create_post_processor(
        self,
        format_name: str,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional['PostProcessorBase']:
        """Create a post processor instance for the given format."""
        if not POSTPROCESSORS_AVAILABLE:
            logger.error("Post processor module not available")
            return None

        # Build config
        config = PostProcessorConfig()
        if config_overrides:
            # Apply overrides
            hooks_data = config_overrides.pop('hooks', None)
            for key, value in config_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            if hooks_data:
                config.hooks = EventHooks.from_dict(hooks_data)

        # Create appropriate processor
        processors = {
            'gcode': GCodePostProcessor,
            'rapid': RAPIDPostProcessor,
            'krl': KRLPostProcessor,
            'fanuc': FanucPostProcessor,
        }

        processor_class = processors.get(format_name)
        if not processor_class:
            logger.error(f"Unknown format: {format_name}")
            return None

        return processor_class(config)

    def export(
        self,
        toolpath_data: Dict[str, Any],
        format_name: str = 'gcode',
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Export toolpath data in the specified format.

        Returns:
            Dict with 'content' (string), 'extension', 'format', 'lines', 'size'.
        """
        processor = self.create_post_processor(format_name, config_overrides)
        if not processor:
            return {
                'error': f"Could not create post processor for format '{format_name}'",
                'content': '',
            }

        try:
            content = processor.generate(toolpath_data)
            line_count = content.count('\n') + 1

            logger.info(
                f"Exported {format_name}: {line_count} lines, "
                f"{len(content)} bytes"
            )

            return {
                'content': content,
                'extension': processor.file_extension,
                'format': format_name,
                'formatName': FORMAT_INFO.get(format_name, {}).get('name', format_name),
                'lines': line_count,
                'size': len(content),
            }
        except Exception as e:
            logger.error(f"Export failed for format {format_name}: {e}", exc_info=True)
            return {
                'error': str(e),
                'content': '',
            }

    def get_default_config(self, format_name: str) -> Dict[str, Any]:
        """Get default configuration for a format."""
        processor = self.create_post_processor(format_name)
        if processor:
            return processor.config.to_dict()
        return PostProcessorConfig().to_dict()
