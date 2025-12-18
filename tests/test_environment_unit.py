"""
Unit tests for Environment Detection functionality in CFN Template Linter.
Minimal fast tests focusing on core functionality.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cfn_linter.environment import EnvironmentManager, EnvironmentDetector, ExecutionContext


class TestEnvironmentDetector:
    """Minimal unit tests for EnvironmentDetector class."""
    
    def test_detector_initialization(self):
        """Test EnvironmentDetector initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            detector = EnvironmentDetector(project_root=temp_path)
            
            assert detector.project_root == temp_path
    
    def test_execution_context_detection(self):
        """Test execution context detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            detector = EnvironmentDetector(project_root=temp_path)
            
            context = detector.detect_execution_context()
            
            # Should return a valid ExecutionContext (including PYTEST)
            assert isinstance(context, ExecutionContext)
            assert context in [ExecutionContext.LOCAL, ExecutionContext.BUILD_PIPELINE, ExecutionContext.PYTEST]


class TestEnvironmentManager:
    """Minimal unit tests for EnvironmentManager class."""
    
    def test_manager_initialization(self):
        """Test EnvironmentManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manager = EnvironmentManager(project_root=temp_path)
            
            # Just test that manager can be created
            assert manager is not None
            assert hasattr(manager, 'detector')