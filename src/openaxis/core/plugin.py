"""
Plugin system for OpenAxis.

Provides base classes and registry for extensible process plugins.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from importlib import import_module
from pathlib import Path
from typing import Any, TypeVar

from openaxis.core.exceptions import PluginError


class ProcessType(Enum):
    """Type of manufacturing process."""

    ADDITIVE = auto()
    SUBTRACTIVE = auto()
    SCANNING = auto()
    HYBRID = auto()


class Plugin(ABC):
    """
    Abstract base class for OpenAxis plugins.

    All process plugins must inherit from this class and implement
    the required abstract methods.
    """

    # Plugin metadata - override in subclasses
    name: str = "base_plugin"
    version: str = "0.0.0"
    description: str = ""
    process_type: ProcessType = ProcessType.ADDITIVE

    @abstractmethod
    def initialize(self, config: dict[str, Any]) -> None:
        """
        Initialize the plugin with configuration.

        Args:
            config: Plugin-specific configuration dictionary
        """
        pass

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    def shutdown(self) -> None:
        """Clean up plugin resources. Override if needed."""
        pass


T = TypeVar("T", bound=Plugin)


@dataclass
class PluginInfo:
    """Information about a registered plugin."""

    name: str
    version: str
    description: str
    process_type: ProcessType
    plugin_class: type[Plugin]
    module_path: str


@dataclass
class PluginRegistry:
    """
    Registry for discovering and managing plugins.

    Supports automatic discovery from specified directories
    and manual registration.

    Example:
        >>> registry = PluginRegistry()
        >>> registry.discover(Path("plugins"))
        >>> waam_plugin = registry.get("waam")
    """

    _plugins: dict[str, PluginInfo] = field(default_factory=dict, init=False)
    _instances: dict[str, Plugin] = field(default_factory=dict, init=False)

    def register(self, plugin_class: type[Plugin]) -> None:
        """
        Register a plugin class.

        Args:
            plugin_class: Plugin class to register

        Raises:
            PluginError: If plugin is invalid or already registered
        """
        if not issubclass(plugin_class, Plugin):
            raise PluginError(
                "Invalid plugin class",
                plugin_name=getattr(plugin_class, "name", "unknown"),
                details={"reason": "Must inherit from Plugin"},
            )

        name = plugin_class.name
        if name in self._plugins:
            raise PluginError(
                f"Plugin already registered: {name}",
                plugin_name=name,
            )

        info = PluginInfo(
            name=name,
            version=plugin_class.version,
            description=plugin_class.description,
            process_type=plugin_class.process_type,
            plugin_class=plugin_class,
            module_path=f"{plugin_class.__module__}.{plugin_class.__name__}",
        )
        self._plugins[name] = info

    def discover(self, plugin_dir: Path) -> list[str]:
        """
        Discover and register plugins from a directory.

        Looks for Python modules with a `register_plugin` function
        or classes inheriting from Plugin.

        Args:
            plugin_dir: Directory to search for plugins

        Returns:
            List of discovered plugin names
        """
        discovered = []
        plugin_dir = Path(plugin_dir)

        if not plugin_dir.exists():
            return discovered

        for module_path in plugin_dir.glob("**/plugin.py"):
            try:
                # Convert path to module name
                relative = module_path.relative_to(plugin_dir)
                module_name = str(relative.with_suffix("")).replace("/", ".")

                module = import_module(f"openaxis.plugins.{module_name}")

                # Look for register_plugin function
                if hasattr(module, "register_plugin"):
                    plugin_class = module.register_plugin()
                    self.register(plugin_class)
                    discovered.append(plugin_class.name)

                # Or find Plugin subclasses directly
                else:
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, Plugin)
                            and attr is not Plugin
                        ):
                            self.register(attr)
                            discovered.append(attr.name)

            except (ImportError, PluginError) as e:
                # Log warning but continue discovering
                print(f"Warning: Failed to load plugin from {module_path}: {e}")

        return discovered

    def get(self, name: str) -> PluginInfo:
        """
        Get plugin info by name.

        Args:
            name: Plugin name

        Returns:
            PluginInfo instance

        Raises:
            PluginError: If plugin not found
        """
        if name not in self._plugins:
            available = list(self._plugins.keys())
            raise PluginError(
                f"Plugin not found: {name}",
                plugin_name=name,
                details={"available": available},
            )
        return self._plugins[name]

    def create_instance(self, name: str, config: dict[str, Any] | None = None) -> Plugin:
        """
        Create a plugin instance.

        Args:
            name: Plugin name
            config: Optional configuration for the plugin

        Returns:
            Initialized plugin instance

        Raises:
            PluginError: If plugin not found or initialization fails
        """
        info = self.get(name)

        try:
            instance = info.plugin_class()
            instance.initialize(config or {})
            self._instances[name] = instance
            return instance
        except Exception as e:
            raise PluginError(
                f"Failed to create plugin instance: {name}",
                plugin_name=name,
                details={"error": str(e)},
            )

    def list_plugins(self) -> list[PluginInfo]:
        """List all registered plugins."""
        return list(self._plugins.values())

    def list_by_type(self, process_type: ProcessType) -> list[PluginInfo]:
        """List plugins of a specific process type."""
        return [p for p in self._plugins.values() if p.process_type == process_type]
