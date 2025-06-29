"""Local .synthdb directory configuration management."""

import os
from pathlib import Path
from typing import Dict, Optional, Any
import configparser


class LocalConfig:
    """Manages the local .synthdb directory and configuration."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the local config manager.
        
        Args:
            base_dir: Base directory to look for .synthdb. Defaults to current directory.
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.synthdb_dir = self._find_synthdb_dir()
        self.config_file = self.synthdb_dir / "config" if self.synthdb_dir else None
        self._config = None
    
    def _find_synthdb_dir(self) -> Optional[Path]:
        """Find the .synthdb directory by searching up the directory tree."""
        current = self.base_dir
        while current != current.parent:
            synthdb_path = current / ".synthdb"
            if synthdb_path.exists() and synthdb_path.is_dir():
                return synthdb_path
            current = current.parent
        
        # Check in the base directory one more time
        synthdb_path = self.base_dir / ".synthdb"
        if synthdb_path.exists() and synthdb_path.is_dir():
            return synthdb_path
        
        return None
    
    def init_synthdb_dir(self, directory: Optional[Path] = None) -> Path:
        """Initialize a new .synthdb directory.
        
        Args:
            directory: Directory to create .synthdb in. Defaults to current directory.
            
        Returns:
            Path to the created .synthdb directory.
        """
        target_dir = Path(directory) if directory else self.base_dir
        synthdb_path = target_dir / ".synthdb"
        
        # Create directory structure
        synthdb_path.mkdir(exist_ok=True)
        (synthdb_path / "databases").mkdir(exist_ok=True)
        
        # Create default config
        self.synthdb_dir = synthdb_path
        self.config_file = synthdb_path / "config"
        self._create_default_config()
        
        return synthdb_path
    
    def _create_default_config(self) -> None:
        """Create a default configuration file."""
        config = configparser.ConfigParser()
        
        # Default database configuration
        config['database'] = {
            'default': '.synthdb/databases/main.db',
            'backend': 'sqlite'
        }
        
        # Branch configuration
        config['branches'] = {
            'active': 'main'
        }
        
        # Branch database locations
        config['branch.main'] = {
            'database': '.synthdb/databases/main.db',
            'created': 'initial'
        }
        
        self._write_config(config)
    
    def _read_config(self) -> configparser.ConfigParser:
        """Read the configuration file."""
        if not self.config_file or not self.config_file.exists():
            return configparser.ConfigParser()
        
        config = configparser.ConfigParser()
        config.read(self.config_file)
        return config
    
    def _write_config(self, config: configparser.ConfigParser) -> None:
        """Write the configuration file."""
        if not self.config_file:
            raise ValueError("No .synthdb directory initialized")
        
        with open(self.config_file, 'w') as f:
            config.write(f)
    
    @property
    def config(self) -> configparser.ConfigParser:
        """Get the current configuration."""
        if self._config is None:
            self._config = self._read_config()
        return self._config
    
    def get_database_path(self, branch: Optional[str] = None) -> Optional[str]:
        """Get the database path for a branch.
        
        Args:
            branch: Branch name. Defaults to active branch.
            
        Returns:
            Database path or None if not found.
        """
        if not self.synthdb_dir:
            return None
        
        if branch is None:
            branch = self.get_active_branch()
        
        branch_section = f'branch.{branch}'
        if branch_section in self.config:
            try:
                db_path = self.config.get(branch_section, 'database')
                if db_path:
                    # Make path relative to the parent of .synthdb
                    if not os.path.isabs(db_path):
                        return str(self.synthdb_dir.parent / db_path)
                    return db_path
            except (configparser.NoSectionError, configparser.NoOptionError):
                pass
        
        # Fallback to default
        try:
            default_path = self.config.get('database', 'default')
            if default_path and not os.path.isabs(default_path):
                return str(self.synthdb_dir.parent / default_path)
            return default_path
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None
    
    def get_active_branch(self) -> str:
        """Get the currently active branch."""
        if not self.synthdb_dir:
            return 'main'
        
        try:
            return self.config.get('branches', 'active')
        except (configparser.NoSectionError, configparser.NoOptionError):
            return 'main'
    
    def set_active_branch(self, branch: str) -> None:
        """Set the active branch."""
        if not self.synthdb_dir:
            raise ValueError("No .synthdb directory initialized")
        
        config = self.config
        if 'branches' not in config:
            config['branches'] = {}
        config['branches']['active'] = branch
        self._write_config(config)
        self._config = None  # Invalidate cache
    
    def create_branch(self, name: str, from_branch: Optional[str] = None) -> str:
        """Create a new branch.
        
        Args:
            name: Branch name.
            from_branch: Branch to copy from. Defaults to active branch.
            
        Returns:
            Path to the new branch's database.
        """
        if not self.synthdb_dir:
            raise ValueError("No .synthdb directory initialized")
        
        if from_branch is None:
            from_branch = self.get_active_branch()
        
        # Create new database path
        db_path = f'.synthdb/databases/{name}.db'
        full_db_path = self.synthdb_dir.parent / db_path
        
        # Copy database if source exists
        from_db = self.get_database_path(from_branch)
        if from_db and Path(from_db).exists():
            import shutil
            full_db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(from_db, full_db_path)
        
        # Update config
        config = self.config
        branch_section = f'branch.{name}'
        config[branch_section] = {
            'database': db_path,
            'created': f'from {from_branch}'
        }
        self._write_config(config)
        self._config = None  # Invalidate cache
        
        return str(full_db_path)
    
    def list_branches(self) -> Dict[str, Dict[str, str]]:
        """List all branches and their configurations.
        
        Returns:
            Dictionary of branch names to their configurations.
        """
        if not self.synthdb_dir:
            return {}
        
        branches = {}
        for section in self.config.sections():
            if section.startswith('branch.'):
                branch_name = section[7:]  # Remove 'branch.' prefix
                branches[branch_name] = dict(self.config[section])
        
        return branches
    
    def get_default_backend(self) -> str:
        """Get the default database backend."""
        if not self.synthdb_dir:
            return 'sqlite'
        
        try:
            return self.config.get('database', 'backend')
        except (configparser.NoSectionError, configparser.NoOptionError):
            return 'sqlite'


# Global instance for convenience
_local_config = None


def get_local_config(base_dir: Optional[Path] = None) -> LocalConfig:
    """Get or create the global LocalConfig instance."""
    global _local_config
    if _local_config is None or base_dir is not None:
        _local_config = LocalConfig(base_dir)
    return _local_config


def init_local_project(directory: Optional[Path] = None) -> Path:
    """Initialize a new SynthDB project in the given directory."""
    config = LocalConfig(directory)
    return config.init_synthdb_dir(directory)