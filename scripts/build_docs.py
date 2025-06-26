#!/usr/bin/env python3
"""
Build script for SynthDB documentation.

This script builds both Sphinx and MkDocs documentation, with options for
development serving and production builds.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True, cwd=None):
    """Run a shell command and return the result."""
    print(f"🔧 Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=check, cwd=cwd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return e


def check_dependencies():
    """Check if documentation dependencies are installed."""
    required_packages = [
        'sphinx',
        'furo',
        'myst-parser',
        'sphinx-copybutton',
        'sphinx-design',
        'mkdocs',
        'mkdocs-material',
        'mkdocstrings[python]',
        'mike'
    ]
    
    missing = []
    # Map package names to their import names
    import_names = {
        'sphinx': 'sphinx',
        'furo': 'furo',
        'myst-parser': 'myst_parser',
        'sphinx-copybutton': 'sphinx_copybutton',
        'sphinx-design': 'sphinx_design',
        'mkdocs': 'mkdocs',
        'mkdocs-material': 'material',
        'mkdocstrings[python]': 'mkdocstrings',
        'mike': 'mike'
    }
    
    for package in required_packages:
        try:
            import_name = import_names.get(package, package.replace('-', '_').split('[')[0])
            __import__(import_name)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing documentation dependencies: {', '.join(missing)}")
        print("Install them with:")
        print(f"  uv add {' '.join(missing)}")
        print("  # or")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)
    
    print("✅ All documentation dependencies are installed")


def clean_build_dirs():
    """Clean previous build directories."""
    dirs_to_clean = [
        "docs/_build",
        "site",
        ".sphinx-build"
    ]
    
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            print(f"🧹 Cleaning {dir_path}")
            shutil.rmtree(dir_path)


def build_sphinx():
    """Build Sphinx documentation."""
    print("\n📚 Building Sphinx documentation...")
    
    # Create build directory
    os.makedirs("docs/_build", exist_ok=True)
    
    # Build HTML docs
    run_command([
        "sphinx-build",
        "-b", "html",
        "-W",  # Turn warnings into errors
        "docs",
        "docs/_build/html"
    ])
    
    print("✅ Sphinx documentation built successfully")
    return "docs/_build/html"


def build_mkdocs():
    """Build MkDocs documentation."""
    print("\n📖 Building MkDocs documentation...")
    
    # Build the site
    run_command(["mkdocs", "build", "--strict"])
    
    print("✅ MkDocs documentation built successfully")
    return "site"


def serve_mkdocs(port=8000):
    """Serve MkDocs documentation for development."""
    print(f"\n🚀 Serving MkDocs documentation on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    
    try:
        run_command(["mkdocs", "serve", "--dev-addr", f"localhost:{port}"])
    except KeyboardInterrupt:
        print("\n👋 Documentation server stopped")


def serve_sphinx(port=8001):
    """Serve Sphinx documentation for development."""
    sphinx_dir = build_sphinx()
    
    print(f"\n🚀 Serving Sphinx documentation on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    
    try:
        run_command([
            "python", "-m", "http.server", str(port)
        ], cwd=sphinx_dir)
    except KeyboardInterrupt:
        print("\n👋 Documentation server stopped")


def deploy_docs():
    """Deploy documentation to GitHub Pages using mike."""
    print("\n🚀 Deploying documentation...")
    
    # Deploy with mike (versioned docs)
    version = get_version()
    
    run_command([
        "mike", "deploy", "--push", "--update-aliases",
        version, "latest"
    ])
    
    # Set default version
    run_command([
        "mike", "set-default", "--push", "latest"
    ])
    
    print("✅ Documentation deployed successfully")


def get_version():
    """Get the current version from pyproject.toml."""
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
    
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    
    return data["project"]["version"]


def generate_api_stubs():
    """Generate API documentation stubs."""
    print("\n📝 Generating API documentation stubs...")
    
    # Create API docs directory
    api_dir = Path("docs/api")
    api_dir.mkdir(exist_ok=True)
    
    # Generate autodoc stubs
    run_command([
        "sphinx-apidoc",
        "-f",  # Force overwrite
        "-o", "docs/api",
        "synthdb",
        "synthdb/tests"
    ])
    
    print("✅ API documentation stubs generated")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Build SynthDB documentation")
    parser.add_argument(
        "action",
        choices=["build", "serve", "serve-sphinx", "serve-mkdocs", "clean", "deploy", "check"],
        help="Action to perform"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for development server (default: 8000)"
    )
    parser.add_argument(
        "--no-sphinx",
        action="store_true",
        help="Skip Sphinx build"
    )
    parser.add_argument(
        "--no-mkdocs",
        action="store_true",
        help="Skip MkDocs build"
    )
    
    args = parser.parse_args()
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    if args.action == "check":
        check_dependencies()
        return
    
    if args.action == "clean":
        clean_build_dirs()
        return
    
    if args.action == "serve-mkdocs":
        check_dependencies()
        serve_mkdocs(args.port)
        return
    
    if args.action == "serve-sphinx":
        check_dependencies()
        serve_sphinx(args.port)
        return
    
    if args.action == "serve":
        check_dependencies()
        serve_mkdocs(args.port)
        return
    
    if args.action == "deploy":
        check_dependencies()
        build_mkdocs()
        deploy_docs()
        return
    
    if args.action == "build":
        check_dependencies()
        clean_build_dirs()
        
        if not args.no_sphinx:
            generate_api_stubs()
            sphinx_output = build_sphinx()
            print(f"\n📁 Sphinx docs: {sphinx_output}")
        
        if not args.no_mkdocs:
            mkdocs_output = build_mkdocs()
            print(f"\n📁 MkDocs site: {mkdocs_output}")
        
        print("\n✅ Documentation build complete!")
        print("\nTo serve locally:")
        print("  python scripts/build_docs.py serve")
        print("\nTo deploy:")
        print("  python scripts/build_docs.py deploy")


if __name__ == "__main__":
    main()