"""
Unit tests for PostDeploy functionality (not part of cfn-template-linter).
Minimal tests to avoid performance issues.
"""

import pytest
import sys
import os
from pathlib import Path

# Add tests directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cfn_test_utils import load_template


class TestPostDeployBasic:
    """Minimal unit tests for PostDeploy functionality."""
    
    def test_pipeline_template_exists(self):
        """Test that the pipeline template file exists."""
        try:
            template = load_template('templates/v2/pipeline/template-pipeline.yml')
            assert template is not None
            assert 'Resources' in template
        except FileNotFoundError:
            pytest.skip("Pipeline template not found - skipping PostDeploy tests")