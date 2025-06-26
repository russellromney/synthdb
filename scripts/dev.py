#!/usr/bin/env python3
"""Development workflow script using uv for fast operations."""

import subprocess
import sys
import argparse
from pathlib import Path


def run_command(cmd: list[str], description: str = "") -> int:
    """Run a command and return its exit code."""
    if description:
        print(f"🔄 {description}")
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"✅ Success: {description}")
    else:
        print(f"❌ Failed: {description}")
    
    return result.returncode


def install_deps():
    """Install dependencies using uv."""
    return run_command(["uv", "sync"], "Installing dependencies with uv")


def install_with_extras(extras: str):
    """Install with specific extras using uv."""
    return run_command(["uv", "sync", "--extra", extras], f"Installing with {extras} extras")


def run_tests():
    """Run tests using pytest."""
    return run_command(["uv", "run", "pytest", "-v", "--cov=synthdb"], "Running tests")


def run_lint():
    """Run linting with ruff."""
    return run_command(["uv", "run", "ruff", "check", "synthdb/"], "Linting code")


def run_format():
    """Format code with ruff."""
    return run_command(["uv", "run", "ruff", "format", "synthdb/"], "Formatting code")


def run_typecheck():
    """Run type checking with mypy."""
    return run_command(["uv", "run", "mypy", "synthdb/"], "Type checking")


def build_package():
    """Build the package."""
    return run_command(["uv", "build"], "Building package")


def clean():
    """Clean build artifacts."""
    import shutil
    
    dirs_to_clean = ["build", "dist", "*.egg-info", "__pycache__"]
    for pattern in dirs_to_clean:
        for path in Path().glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"Removed directory: {path}")
            else:
                path.unlink()
                print(f"Removed file: {path}")
    
    print("✅ Cleaned build artifacts")
    return 0


def dev_setup():
    """Complete development setup."""
    print("🚀 Setting up SynthDB development environment with uv")
    
    steps = [
        (install_deps, "Installing base dependencies"),
        (lambda: install_with_extras("config"), "Installing config extras"),
        (lambda: install_with_extras("dev"), "Installing dev dependencies"),
    ]
    
    for step_func, description in steps:
        if step_func() != 0:
            print(f"❌ Setup failed at: {description}")
            return 1
    
    print("✅ Development environment ready!")
    return 0


def ci_workflow():
    """Run full CI workflow."""
    print("🔄 Running CI workflow")
    
    steps = [
        (run_lint, "Linting"),
        (run_typecheck, "Type checking"),
        (run_tests, "Testing"),
        (build_package, "Building"),
    ]
    
    for step_func, description in steps:
        if step_func() != 0:
            print(f"❌ CI failed at: {description}")
            return 1
    
    print("✅ CI workflow completed successfully!")
    return 0


def main():
    parser = argparse.ArgumentParser(description="SynthDB development workflow with uv")
    parser.add_argument("command", choices=[
        "setup", "install", "test", "lint", "format", "typecheck", 
        "build", "clean", "ci", "dev"
    ], help="Command to run")
    
    parser.add_argument("--extras", help="Extras to install (e.g., 'config,dev')")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        return dev_setup()
    elif args.command == "install":
        if args.extras:
            return install_with_extras(args.extras)
        return install_deps()
    elif args.command == "test":
        return run_tests()
    elif args.command == "lint":
        return run_lint()
    elif args.command == "format":
        return run_format()
    elif args.command == "typecheck":
        return run_typecheck()
    elif args.command == "build":
        return build_package()
    elif args.command == "clean":
        return clean()
    elif args.command == "ci":
        return ci_workflow()
    elif args.command == "dev":
        return dev_setup()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())