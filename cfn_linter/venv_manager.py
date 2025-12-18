"""
Virtual Environment Manager for CFN Template Linter.
Handles .venv virtual environment creation, dependency management, and path resolution.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


class VirtualEnvManager:
    """Manages .venv virtual environment for cfn-lint dependency isolation."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the virtual environment manager.
        
        Args:
            project_root: Path to project root. If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()
        self.venv_path = self.project_root / ".venv"
        
        # Determine OS-specific paths
        if os.name == 'nt':  # Windows
            self.bin_dir = self.venv_path / "Scripts"
            self.python_executable = "python.exe"
            self.pip_executable = "pip.exe"
        else:  # Unix/Linux/macOS
            self.bin_dir = self.venv_path / "bin"
            self.python_executable = "python"
            self.pip_executable = "pip"
    
    def ensure_venv_exists(self) -> bool:
        """Ensure .venv virtual environment exists.
        
        Returns:
            True if virtual environment exists or was created successfully, False otherwise.
        """
        try:
            if self.venv_path.exists() and self._is_valid_venv():
                return True
            
            # Create virtual environment
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(self.venv_path)],
                capture_output=True,
                text=True,
                check=True
            )
            
            return self._is_valid_venv()
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error creating virtual environment: {e}")
            return False
    
    def _is_valid_venv(self) -> bool:
        """Check if the virtual environment is valid."""
        python_path = self.bin_dir / self.python_executable
        return python_path.exists() and python_path.is_file()
    
    def install_dependencies(self) -> bool:
        """Install required dependencies in the virtual environment.
        
        Returns:
            True if dependencies were installed successfully, False otherwise.
        """
        if not self.ensure_venv_exists():
            return False
        
        try:
            pip_path = self.bin_dir / self.pip_executable
            
            # Upgrade pip first
            subprocess.run(
                [str(pip_path), "install", "--upgrade", "pip"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Install from requirements.txt if it exists
            requirements_file = self.project_root / "tests" / "requirements.txt"
            if requirements_file.exists():
                subprocess.run(
                    [str(pip_path), "install", "-r", str(requirements_file)],
                    capture_output=True,
                    text=True,
                    check=True
                )
            else:
                # Install cfn-lint directly
                subprocess.run(
                    [str(pip_path), "install", "cfn-lint>=0.83.0"],
                    capture_output=True,
                    text=True,
                    check=True
                )
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error installing dependencies: {e}")
            return False
    
    def get_cfn_lint_path(self) -> str:
        """Get the path to cfn-lint executable within the virtual environment.
        
        Returns:
            Path to cfn-lint executable as string.
            
        Raises:
            RuntimeError: If virtual environment doesn't exist or cfn-lint is not installed.
        """
        if not self.ensure_venv_exists():
            raise RuntimeError("Virtual environment does not exist")
        
        cfn_lint_path = self.bin_dir / "cfn-lint"
        if os.name == 'nt':  # Windows
            cfn_lint_path = self.bin_dir / "cfn-lint.exe"
        
        if not cfn_lint_path.exists():
            # Try to install dependencies if cfn-lint is missing
            if not self.install_dependencies():
                raise RuntimeError("cfn-lint is not installed and dependency installation failed")
            
            # Check again after installation
            if not cfn_lint_path.exists():
                raise RuntimeError("cfn-lint executable not found after installation")
        
        return str(cfn_lint_path)
    
    def get_python_path(self) -> str:
        """Get the path to Python executable within the virtual environment.
        
        Returns:
            Path to Python executable as string.
            
        Raises:
            RuntimeError: If virtual environment doesn't exist.
        """
        if not self.ensure_venv_exists():
            raise RuntimeError("Virtual environment does not exist")
        
        python_path = self.bin_dir / self.python_executable
        return str(python_path)
    
    def is_cfn_lint_available(self) -> bool:
        """Check if cfn-lint is available in the virtual environment.
        
        Returns:
            True if cfn-lint is available, False otherwise.
        """
        try:
            cfn_lint_path = self.get_cfn_lint_path()
            # Test if cfn-lint can be executed
            result = subprocess.run(
                [cfn_lint_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def setup_environment(self) -> bool:
        """Complete environment setup: create venv and install dependencies.
        
        Returns:
            True if setup was successful, False otherwise.
        """
        if not self.ensure_venv_exists():
            return False
        
        if not self.install_dependencies():
            return False
        
        return self.is_cfn_lint_available()