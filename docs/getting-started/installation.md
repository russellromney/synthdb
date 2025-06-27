# Installation

This guide will help you install SynthDB and get it running on your system.

## Requirements

- Python 3.11 or higher
- uv or pip package manager

## Quick Installation

### 🚀 Recommended: Install with uv

[uv](https://github.com/astral-sh/uv) is the fastest Python package manager and installer:

```bash
# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install SynthDB
uv add synthdb
```

### Alternative Installation with pip

```bash
uv add synthdb
```

## Database Backend

SynthDB uses SQLite as its default database backend:

### SQLite (Default)
- **Battle-tested**: Proven reliability with billions of deployments
- **Maximum compatibility**: Works on all platforms and architectures
- **Zero configuration**: No setup required, included with Python
- **Embedded database**: Perfect for desktop apps and local development

### LibSQL (Optional)
- **SQLite-compatible**: 100% compatible with SQLite databases and APIs
- **Additional features**: Remote database support, edge computing capabilities
- **Remote databases**: Connect to Turso and other LibSQL-compatible services
- **Installation**: Install separately with `uv add libsql-experimental`

## Optional Dependencies

### Configuration File Support

For YAML and TOML configuration file support:

```bash
# With uv
uv add "synthdb[config]"

# With pip (if not using uv)
pip install "synthdb[config]"
```

## Development Installation

If you want to contribute to SynthDB or run the latest development version:

```bash
# Clone the repository
git clone https://github.com/russellromney/synthdb
cd synthdb

# With uv (recommended - 10-100x faster!)
uv sync                 # Install dependencies
make dev               # Setup development environment
make test              # Run tests
make lint              # Run linting

# With pip (if not using uv)
pip install -e ".[dev]"
```

## Verify Installation

After installation, verify that SynthDB is working:

```bash
# Check version
python -c "import synthdb; print(synthdb.__version__)"

# Test basic functionality
python -c "
import synthdb
db = synthdb.connect('test.db')
db.create_table('test')
print('✅ SynthDB is working!')
print(f'Using backend: {db.backend.get_name()}')
"

# Test remote database connection (if you have a Turso database)
# python -c "import synthdb; db = synthdb.connect('libsql://your-db.turso.io'); print('✅ Remote connection working!')"

# Test CLI
synthdb --help
# or use the shorter alias:
sdb --help
```

## Environment Variables

You can configure SynthDB behavior with environment variables:

```bash
# Set default database path
export SYNTHDB_DEFAULT_PATH=myapp.db

# Set default backend (sqlite or libsql)
export SYNTHDB_BACKEND=sqlite  # Default
# export SYNTHDB_BACKEND=libsql  # Use LibSQL for remote features
```

## Troubleshooting

### LibSQL Installation (Optional)

To use LibSQL for remote database support:

```bash
# Install LibSQL support with uv
uv add libsql-experimental

# Or with pip (if not using uv)
pip install libsql-experimental
```

### Common Issues

#### Permission errors
```
Permission denied: Cannot write to database file
```

Make sure you have write permissions to the directory where you're creating the database file.

#### Import errors
```
ModuleNotFoundError: No module named 'synthdb'
```

Make sure you've activated the correct Python environment where SynthDB is installed.

#### Using LibSQL backend
```
Info: Using LibSQL backend for remote database support
```

If you want to use LibSQL features for remote databases:
```bash
uv add libsql-experimental
```

### Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](../advanced/troubleshooting.md)
2. Search [existing issues](https://github.com/russellromney/synthdb/issues)
3. Create a [new issue](https://github.com/russellromney/synthdb/issues/new)

## Next Steps

Now that SynthDB is installed, continue with:

- [Quick Start Guide](quickstart.md) - Get up and running in minutes
- [Basic Concepts](concepts.md) - Understand how SynthDB works
- [Connection API](../user-guide/connection-api.md) - Learn the Python API