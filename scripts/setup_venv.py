#!/usr/bin/env python3
"""
Virtual environment setup script for CFN Template Linter.
Creates and configures .venv with required dependencies.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, cwd=None, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}")
        print(f"Error: {e.stderr}")
        raise


def setup_virtual_environment():
    """Set up .venv virtual environment with required dependencies."""
    project_root = Path(__file__).parent
    venv_path = project_root / ".venv"
    
    print("Setting up virtual environment for CFN Template Linter...")
    
    # Create virtual environment if it doesn't exist
    if not venv_path.exists():
        print(f"Creating virtual environment at {venv_path}")
        run_command(f"{sys.executable} -m venv {venv_path}")
    else:
        print(f"Virtual environment already exists at {venv_path}")
    
    # Determine pip path based on OS
    if os.name == 'nt':  # Windows
        pip_path = venv_path / "Scripts" / "pip"
        python_path = venv_path / "Scripts" / "python"
    else:  # Unix/Linux/macOS
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
    
    # Upgrade pip
    print("Upgrading pip...")
    run_command(f"{python_path} -m pip install --upgrade pip")
    
    # Install test dependencies
    requirements_file = project_root / "tests" / "requirements.txt"
    if requirements_file.exists():
        print(f"Installing dependencies from {requirements_file}")
        run_command(f"{pip_path} install -r {requirements_file}")
    else:
        print("Warning: tests/requirements.txt not found, installing cfn-lint directly")
        run_command(f"{pip_path} install cfn-lint>=0.83.0")
    
    print("Virtual environment setup complete!")
    print(f"To activate: source {venv_path}/bin/activate (Linux/macOS) or {venv_path}\\Scripts\\activate (Windows)")
    
    return venv_path


if __name__ == "__main__":
    try:
        venv_path = setup_virtual_environment()
        print(f"Success: Virtual environment created at {venv_path}")
    except Exception as e:
        print(f"Error setting up virtual environment: {e}")
        sys.exit(1)