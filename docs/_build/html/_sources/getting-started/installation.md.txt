# Installation

This guide will help you install SynthDB and get it running on your system.

## Requirements

- Python 3.8 or higher
- pip or uv package manager

## Quick Installation

### 🚀 Recommended: Install with uv

[uv](https://github.com/astral-sh/uv) is the fastest Python package manager and installer:

```bash
# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install SynthDB
uv add synthdb
```

### Traditional Installation with pip

```bash
pip install synthdb
```

## Backend Options

SynthDB supports two database backends:

### Limbo (Default)
- **Pros**: Fastest performance, modern Rust implementation, SQLite-compatible
- **Cons**: Alpha software, may have compatibility issues
- **Best for**: Development, single-user applications, performance testing

### SQLite (Stable)
- **Pros**: Battle-tested, maximum compatibility, stable, embedded
- **Cons**: Limited concurrent writes
- **Best for**: Production apps, desktop apps, small web apps, embedded systems

The Limbo backend is automatically installed with SynthDB. If it's not available on your system, SynthDB will automatically fall back to SQLite.

## Optional Dependencies

### Configuration File Support

For YAML and TOML configuration file support:

```bash
# With uv
uv add "synthdb[config]"

# With pip
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

# With pip (traditional)
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
db = synthdb.connect('test.limbo')  # Uses Limbo by default
db.create_table('test')
print('✅ SynthDB is working!')
"

# Test CLI
synthdb --help
# or use the shorter alias:
sdb --help
```

## Environment Variables

You can configure SynthDB behavior with environment variables:

```bash
# Set default backend (optional - Limbo is already default)
export SYNTHDB_BACKEND=limbo

# Set default database path
export SYNTHDB_DEFAULT_PATH=myapp.limbo
```

## Troubleshooting

### Common Issues

#### Limbo backend not available
```
Warning: Limbo backend not available, falling back to SQLite
```

This is normal and not an error. SynthDB will use SQLite as the backend, which works perfectly for all operations.

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