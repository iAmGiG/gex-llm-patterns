"""Configuration Manager Centralized configuration loading with environment override support."""

import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

logger = logging.getLogger(__name__)


class ConfigManager:
    """Centralized configuration manager for system parameters.

    Loads configuration from YAML files with environment variable override support. Provides dot-notation access to
    nested configuration values.
    """

    def __init__(self, config_dir: Optional[str] = None, environment: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Path to configuration directory (default: project_root/config_defaults)
            environment: Environment name for config overrides (default: from ENV var)
        """
        self.config_dir = Path(config_dir) if config_dir else self._get_default_config_dir()
        self.environment = environment or os.getenv("ENVIRONMENT", "default")
        self._config_cache = {}

        # Load all configuration files
        self._load_all_configs()

        logger.info(f"ConfigManager initialized: {self.config_dir}, env: {self.environment}")

    def _get_default_config_dir(self) -> Path:
        """Get default configuration directory relative to project root."""
        # Find project root (where config_defaults should be)
        current = Path(__file__)
        while current.parent != current:
            if (current / "config_defaults").exists():
                return current / "config_defaults"
            current = current.parent

        # Fallback to relative path
        return Path(__file__).parent.parent.parent / "config_defaults"

    def _load_all_configs(self):
        """Load all YAML configuration files from the config directory."""
        if not self.config_dir.exists():
            logger.warning(f"Configuration directory not found: {self.config_dir}")
            return

        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)

                # Use filename (without extension) as config section name
                section_name = config_file.stem.replace("_config", "")
                self._config_cache[section_name] = config_data

                logger.debug(f"Loaded config section '{section_name}' from {config_file}")

            except Exception as e:
                logger.error(f"Failed to load config file {config_file}: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path to configuration value (e.g., 'tokenization.gex.lookback_days')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            config.get('tokenization.gex.lookback_days')
            config.get('analysis.confidence.base_lookback', 252)
        """
        # Check for environment variable override first
        env_var = self._key_path_to_env_var(key_path)
        env_value = os.getenv(env_var)
        if env_value is not None:
            return self._parse_env_value(env_value)

        # Navigate through nested dictionary
        parts = key_path.split(".")
        current = self._config_cache

        try:
            for part in parts:
                current = current[part]
            return current
        except (KeyError, TypeError):
            logger.debug(f"Configuration key not found: {key_path}, using default: {default}")
            return default

    def _key_path_to_env_var(self, key_path: str) -> str:
        """Convert dot notation key path to environment variable name."""
        return key_path.upper().replace(".", "_")

    def _parse_env_value(self, value: str) -> Union[str, int, float, bool, list]:
        """Parse environment variable value to appropriate Python type."""
        # Try boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Try integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try float
        try:
            return float(value)
        except ValueError:
            pass

        # Try list (comma-separated)
        if "," in value:
            try:
                return [self._parse_env_value(item.strip()) for item in value.split(",")]
            except:
                pass

        # Return as string
        return value

    def get_section(self, section_name: str) -> Dict[str, Any]:
        """Get entire configuration section.

        Args:
            section_name: Name of configuration section

        Returns:
            Dictionary with section configuration
        """
        return self._config_cache.get(section_name, {})

    def has_key(self, key_path: str) -> bool:
        """Check if configuration key exists."""
        try:
            self.get(key_path)
            return True
        except:
            return False

    def list_keys(self, section: Optional[str] = None) -> list:
        """List all available configuration keys.

        Args:
            section: Specific section to list (None for all)

        Returns:
            List of available configuration key paths
        """
        keys = []

        if section:
            section_data = self._config_cache.get(section, {})
            keys.extend(self._flatten_keys(section_data, prefix=section))
        else:
            for section_name, section_data in self._config_cache.items():
                keys.extend(self._flatten_keys(section_data, prefix=section_name))

        return sorted(keys)

    def _flatten_keys(self, data: Dict[str, Any], prefix: str = "") -> list:
        """Recursively flatten nested dictionary keys to dot notation."""
        keys = []

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                keys.extend(self._flatten_keys(value, full_key))
            else:
                keys.append(full_key)

        return keys

    def reload(self):
        """Reload all configuration files."""
        self._config_cache.clear()
        self._load_all_configs()
        logger.info("Configuration reloaded")

    def validate_required_keys(self, required_keys: list) -> Dict[str, bool]:
        """Validate that required configuration keys are present.

        Args:
            required_keys: List of required key paths

        Returns:
            Dictionary mapping key -> is_present
        """
        results = {}
        for key in required_keys:
            try:
                value = self.get(key)
                results[key] = value is not None
            except:
                results[key] = False

        return results

    def get_effective_config(self) -> Dict[str, Any]:
        """Get complete effective configuration (useful for debugging)."""
        return dict(self._config_cache)


# Global instance for easy access with thread-safe initialization
_global_config_manager = None
_config_lock = threading.Lock()


def get_config() -> ConfigManager:
    """Get global configuration manager instance (thread-safe singleton)."""
    global _global_config_manager
    if _global_config_manager is None:
        with _config_lock:
            # Double-check locking pattern
            if _global_config_manager is None:
                _global_config_manager = ConfigManager()
    return _global_config_manager


def reset_config() -> None:
    """Reset the global config manager (for testing)."""
    global _global_config_manager
    with _config_lock:
        _global_config_manager = None
