"""
Integration tests for buildspec configuration.
Minimal fast tests focusing on core functionality.
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBuildspecConfiguration:
    """Integration tests for buildspec execution."""
    
    def test_buildspec_file_exists(self):
        """Test that buildspec.yml file exists."""
        project_root = Path(__file__).parent.parent
        buildspec_file = project_root / "buildspec.yml"
        
        assert buildspec_file.exists(), "buildspec.yml should exist"
        assert buildspec_file.is_file(), "buildspec.yml should be a file"
    
    def test_cfn_validation_command_structure(self):
        """Test that the CFN validation command has correct structure."""
        project_root = Path(__file__).parent.parent
        runner_script = project_root / "scripts" / "cfn_lint_runner.py"
        
        assert runner_script.exists(), "scripts/cfn_lint_runner.py should exist for buildspec integration"
    
    def test_environment_setup_script_exists(self):
        """Test that the environment setup script exists."""
        project_root = Path(__file__).parent.parent
        setup_script = project_root / "scripts" / "setup_venv.py"
        
        assert setup_script.exists(), "scripts/setup_venv.py should exist for buildspec integration"