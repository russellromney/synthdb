"""Auto-completion support for SynthDB CLI."""

import os
from typing import List, Optional
from pathlib import Path


def get_table_names(incomplete: str) -> List[str]:
    """Get table names for auto-completion."""
    try:
        from . import list_tables
        tables = list_tables('db.db', backend_name=None)
        table_names = [t['name'] for t in tables]
        
        # Filter by incomplete text
        return [name for name in table_names if name.startswith(incomplete)]
    except Exception:
        # Return empty list if we can't get tables
        return []


def get_column_names(incomplete: str) -> List[str]:
    """Get column names for auto-completion."""
    # For now, return common column names
    # In a full implementation, we'd need context to know which table
    common_columns = ['id', 'name', 'created_at', 'updated_at', 'value', 'data', 'type']
    return [name for name in common_columns if name.startswith(incomplete)]


def get_data_types(incomplete: str) -> List[str]:
    """Get data types for auto-completion."""
    types = ["text", "integer", "real", "timestamp"]
    return [t for t in types if t.startswith(incomplete)]


def get_backends(incomplete: str) -> List[str]:
    """Get available backends for auto-completion."""
    backends = ["sqlite", "libsql"]
    return [b for b in backends if b.startswith(incomplete)]


def get_config_formats(incomplete: str) -> List[str]:
    """Get config file formats for auto-completion."""
    formats = ["json", "yaml", "toml"]
    return [f for f in formats if f.startswith(incomplete)]


def get_connection_names(incomplete: str) -> List[str]:
    """Get named connections for auto-completion."""
    try:
        from .config_file import config_manager
        config = config_manager.get_config()
        connections = list(config.get('connections', {}).keys())
        return [name for name in connections if name.startswith(incomplete)]
    except Exception:
        return []


def get_csv_files(incomplete: str) -> List[str]:
    """Get CSV files for auto-completion."""
    return get_files_with_extension(incomplete, ['.csv'])


def get_json_files(incomplete: str) -> List[str]:
    """Get JSON files for auto-completion."""
    return get_files_with_extension(incomplete, ['.json', '.jsonl'])


def get_config_files(incomplete: str) -> List[str]:
    """Get config files for auto-completion."""
    return get_files_with_extension(incomplete, ['.json', '.yaml', '.yml', '.toml'])


def get_files_with_extension(incomplete: str, extensions: List[str]) -> List[str]:
    """Get files with specific extensions for auto-completion."""
    try:
        # Handle path completion
        if '/' in incomplete:
            dir_path = str(Path(incomplete).parent)
            file_prefix = Path(incomplete).name
        else:
            dir_path = '.'
            file_prefix = incomplete
        
        matches = []
        try:
            for item in Path(dir_path).iterdir():
                if item.is_file() and any(item.suffix.lower() == ext for ext in extensions):
                    if item.name.startswith(file_prefix):
                        if dir_path == '.':
                            matches.append(item.name)
                        else:
                            matches.append(str(item))
                elif item.is_dir() and item.name.startswith(file_prefix):
                    # Include directories for navigation
                    if dir_path == '.':
                        matches.append(f"{item.name}/")
                    else:
                        matches.append(f"{item}/")
        except PermissionError:
            pass
        
        return matches
    except Exception:
        return []


def get_output_formats(incomplete: str) -> List[str]:
    """Get output formats for auto-completion."""
    formats = ["table", "json", "csv"]
    return [f for f in formats if f.startswith(incomplete)]


def complete_file_path(incomplete: str) -> List[str]:
    """Generic file path completion."""
    try:
        if '/' in incomplete:
            dir_path = str(Path(incomplete).parent)
            file_prefix = Path(incomplete).name
        else:
            dir_path = '.'
            file_prefix = incomplete
        
        matches = []
        try:
            for item in Path(dir_path).iterdir():
                if item.name.startswith(file_prefix):
                    if item.is_dir():
                        if dir_path == '.':
                            matches.append(f"{item.name}/")
                        else:
                            matches.append(f"{item}/")
                    else:
                        if dir_path == '.':
                            matches.append(item.name)
                        else:
                            matches.append(str(item))
        except PermissionError:
            pass
        
        return matches
    except Exception:
        return []


def setup_completion():
    """Setup shell completion for SynthDB."""
    import typer
    
    completion_script = """
# SynthDB completion setup
# Add this to your shell configuration file:

# For Bash (.bashrc or .bash_profile):
eval "$(_SDB_COMPLETE=bash_source sdb)"

# For Zsh (.zshrc):
eval "$(_SDB_COMPLETE=zsh_source sdb)"

# For Fish (config.fish):
eval (env _SDB_COMPLETE=fish_source sdb)
"""
    
    return completion_script


def install_completion(shell: str = None):
    """Install shell completion for SynthDB."""
    import subprocess
    import sys
    
    if not shell:
        # Try to detect shell
        shell = os.environ.get('SHELL', '').split('/')[-1]
        if not shell:
            print("Could not detect shell. Please specify with --shell option.")
            return False
    
    if shell == 'bash':
        completion_cmd = "_SDB_COMPLETE=bash_source sdb"
        config_file = Path.home() / '.bashrc'
    elif shell == 'zsh':
        completion_cmd = "_SDB_COMPLETE=zsh_source sdb"
        config_file = Path.home() / '.zshrc'
    elif shell == 'fish':
        completion_cmd = "_SDB_COMPLETE=fish_source sdb"
        config_file = Path.home() / '.config' / 'fish' / 'config.fish'
    else:
        print(f"Unsupported shell: {shell}")
        return False
    
    try:
        # Generate completion script
        result = subprocess.run(
            completion_cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            env={**os.environ, f'_SDB_COMPLETE': f'{shell}_source'}
        )
        
        if result.returncode != 0:
            print(f"Error generating completion: {result.stderr}")
            return False
        
        completion_script = result.stdout
        
        # Check if already installed
        if config_file.exists():
            content = config_file.read_text()
            if 'sdb' in content and 'COMPLETE' in content:
                print(f"Completion already installed in {config_file}")
                return True
        
        # Install completion
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'a') as f:
            f.write(f"\n# SynthDB completion\n")
            f.write(f"eval \"$({completion_cmd})\"\n")
        
        print(f"Completion installed in {config_file}")
        print(f"Restart your shell or run: source {config_file}")
        return True
        
    except Exception as e:
        print(f"Error installing completion: {e}")
        return False