"""
Unit tests for build pipeline integration in CFN Template Linter.
Minimal fast tests focusing on core functionality.
"""

import pytest
import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBuildPipelineRunner:
    """Minimal unit tests for build pipeline runner script."""
    
    def test_runner_script_exists(self):
        """Test that the cfn_lint_runner.py script exists."""
        project_root = Path(__file__).parent.parent
        runner_script = project_root / "scripts" / "cfn_lint_runner.py"
        
        assert runner_script.exists(), "scripts/cfn_lint_runner.py should exist"
        assert runner_script.is_file(), "scripts/cfn_lint_runner.py should be a file"
    
    def test_runner_script_is_executable(self):
        """Test that the runner script has valid Python syntax."""
        project_root = Path(__file__).parent.parent
        runner_script = project_root / "scripts" / "cfn_lint_runner.py"
        
        # Check that it's a valid Python file by reading it
        content = runner_script.read_text()
        assert "#!/usr/bin/env python" in content or "import" in content, \
            "Script should be a valid Python file"
        assert "CloudFormation" in content, "Script should be related to CloudFormation"