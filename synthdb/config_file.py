"""Configuration file support for SynthDB."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None

try:
    import toml
except ImportError:
    toml = None


class ConfigManager:
    """Manages SynthDB configuration files."""
    
    def __init__(self):
        self.config_search_paths = [
            Path.cwd() / ".synthdb.json",
            Path.cwd() / ".synthdb.yaml", 
            Path.cwd() / ".synthdb.yml",
            Path.cwd() / ".synthdb.toml",
            Path.cwd() / "synthdb.config.json",
            Path.cwd() / "synthdb.config.yaml",
            Path.cwd() / "synthdb.config.yml",
            Path.cwd() / "synthdb.config.toml",
            Path.home() / ".config" / "synthdb" / "config.json",
            Path.home() / ".config" / "synthdb" / "config.yaml",
            Path.home() / ".config" / "synthdb" / "config.yml",
            Path.home() / ".config" / "synthdb" / "config.toml",
            Path.home() / ".synthdb" / "config.json",
            Path.home() / ".synthdb" / "config.yaml",
            Path.home() / ".synthdb" / "config.yml",
            Path.home() / ".synthdb" / "config.toml",
        ]
        self._config_cache = None
        self._config_path = None
    
    def find_config_file(self) -> Optional[Path]:
        """Find the first available configuration file."""
        for path in self.config_search_paths:
            if path.exists() and path.is_file():
                return path
        return None
    
    def load_config(self, config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """Load configuration from file or return default config."""
        if config_path:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {config_file}")
        else:
            config_file = self.find_config_file()
            if not config_file:
                return self.get_default_config()
        
        try:
            return self._load_config_file(config_file)
        except Exception as e:
            raise ValueError(f"Error loading config file {config_file}: {e}")
    
    def _load_config_file(self, config_file: Path) -> Dict[str, Any]:
        """Load configuration from a specific file."""
        suffix = config_file.suffix.lower()
        
        with open(config_file, 'r', encoding='utf-8') as f:
            if suffix == '.json':
                config = json.load(f)
            elif suffix in ('.yaml', '.yml'):
                if yaml is None:
                    raise ImportError("PyYAML is required for YAML config files. Install with: pip install PyYAML")
                config = yaml.safe_load(f)
            elif suffix == '.toml':
                if toml is None:
                    raise ImportError("toml is required for TOML config files. Install with: pip install toml")
                config = toml.load(f)
            else:
                raise ValueError(f"Unsupported config file format: {suffix}")
        
        # Validate and normalize config
        return self._normalize_config(config or {})
    
    def _normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate configuration."""
        normalized = self.get_default_config()
        
        # Update with user config
        if 'database' in config:
            normalized['database'].update(config['database'])
        
        if 'connections' in config:
            normalized['connections'].update(config['connections'])
        
        if 'defaults' in config:
            normalized['defaults'].update(config['defaults'])
        
        if 'cli' in config:
            normalized['cli'].update(config['cli'])
        
        return normalized
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'database': {
                'default_backend': 'limbo',
                'default_path': 'db.db',
                'batch_size': 1000,
                'timeout': 30
            },
            'connections': {
                # Named connections can be defined here
            },
            'defaults': {
                'auto_create_columns': True,
                'auto_infer_types': True,
                'show_progress': True,
                'output_format': 'table'
            },
            'cli': {
                'auto_completion': True,
                'color_output': True,
                'confirm_destructive': True,
                'max_rows_display': 100
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get cached configuration or load from file."""
        if self._config_cache is None:
            self._config_cache = self.load_config()
        return self._config_cache
    
    def get_connection_info(self, name: str = None) -> Dict[str, Any]:
        """Get connection information by name or default."""
        config = self.get_config()
        
        if name:
            if name in config['connections']:
                return config['connections'][name]
            else:
                raise ValueError(f"Connection '{name}' not found in config")
        
        # Return default connection info
        return {
            'backend': config['database']['default_backend'],
            'path': config['database']['default_path']
        }
    
    def save_config(self, config: Dict[str, Any], config_path: Union[str, Path] = None) -> None:
        """Save configuration to file."""
        if config_path:
            config_file = Path(config_path)
        else:
            # Use first writable location
            config_file = Path.cwd() / ".synthdb.json"
        
        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine format from extension
        suffix = config_file.suffix.lower()
        
        with open(config_file, 'w', encoding='utf-8') as f:
            if suffix == '.json':
                json.dump(config, f, indent=2)
            elif suffix in ('.yaml', '.yml'):
                if yaml is None:
                    raise ImportError("PyYAML is required for YAML config files. Install with: pip install PyYAML")
                yaml.dump(config, f, default_flow_style=False, indent=2)
            elif suffix == '.toml':
                if toml is None:
                    raise ImportError("toml is required for TOML config files. Install with: pip install toml")
                toml.dump(config, f)
            else:
                # Default to JSON
                json.dump(config, f, indent=2)
    
    def create_sample_config(self, config_path: Union[str, Path], format: str = 'json') -> None:
        """Create a sample configuration file."""
        config = self.get_default_config()
        
        # Add some example connections
        config['connections'] = {
            'local': {
                'backend': 'sqlite',
                'path': './local.db'
            },
            'development': {
                'backend': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'database': 'synthdb_dev',
                'user': 'developer',
                'password': '${DEV_DB_PASSWORD}'  # Environment variable
            },
            'production': {
                'backend': 'postgresql',
                'host': 'production-db.example.com',  # Replace with your production host
                'port': 5432,
                'database': 'synthdb_prod',
                'user': 'app_user',
                'password': '${SYNTHDB_PASSWORD}'  # Environment variable
            }
        }
        
        if format == 'yaml':
            config_path = Path(config_path).with_suffix('.yaml')
        elif format == 'toml':
            config_path = Path(config_path).with_suffix('.toml')
        else:
            config_path = Path(config_path).with_suffix('.json')
        
        self.save_config(config, config_path)
    
    def resolve_env_vars(self, value: Any) -> Any:
        """Resolve environment variables in configuration values."""
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        elif isinstance(value, dict):
            return {k: self.resolve_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve_env_vars(item) for item in value]
        else:
            return value
    
    def get_resolved_connection(self, name: str = None) -> Dict[str, Any]:
        """Get connection info with environment variables resolved."""
        connection = self.get_connection_info(name)
        return self.resolve_env_vars(connection)


# Global config manager instance
config_manager = ConfigManager()


def get_config() -> Dict[str, Any]:
    """Get the current configuration."""
    return config_manager.get_config()


def get_connection_info(name: str = None) -> Dict[str, Any]:
    """Get connection information."""
    return config_manager.get_resolved_connection(name)


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from file."""
    return config_manager.load_config(config_path)


def save_config(config: Dict[str, Any], config_path: str = None) -> None:
    """Save configuration to file."""
    config_manager.save_config(config, config_path)


def create_sample_config(config_path: str = ".synthdb.json", format: str = 'json') -> None:
    """Create a sample configuration file."""
    config_manager.create_sample_config(config_path, format)