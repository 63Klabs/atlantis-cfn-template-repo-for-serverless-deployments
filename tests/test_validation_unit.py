"""
Unit tests for CloudFormation Validation functionality in CFN Template Linter.
Minimal fast tests focusing on core functionality.
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
import yaml

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cfn_linter.validation import CFNValidator, ValidationResult, ValidationSummary, ValidationError


class TestCFNValidator:
    """Minimal unit tests for CFNValidator class."""
    
    def test_validator_initialization(self):
        """Test CFNValidator initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            validator = CFNValidator(project_root=temp_path)
            
            assert validator.project_root == temp_path
            assert hasattr(validator, 'venv_manager')
    
    def test_validate_nonexistent_template(self):
        """Test validation of non-existent template file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            nonexistent_file = temp_path / "nonexistent.yml"
            
            validator = CFNValidator(project_root=temp_path)
            result = validator.validate_template(nonexistent_file)
            
            assert isinstance(result, ValidationResult)
            assert result.template_path == nonexistent_file
            assert result.is_valid == False
            assert len(result.errors) > 0
            
            error = result.errors[0]
            assert error.rule_id is not None
    
    def test_validate_all_templates_empty_list(self):
        """Test validation of empty template list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            validator = CFNValidator(project_root=temp_path)
            
            summary = validator.validate_all_templates([])
            
            assert isinstance(summary, ValidationSummary)
            assert summary.total_templates == 0
            assert summary.valid_templates == 0
            assert summary.failed_templates == 0
            assert len(summary.results) == 0
            assert isinstance(summary.execution_time, float)


class TestValidationDataModels:
    """Unit tests for validation data model classes."""
    
    def test_validation_error_creation(self):
        """Test ValidationError data model creation."""
        error = ValidationError(
            rule_id='E1001',
            message='Test error message',
            line_number=10,
            column_number=5,
            severity='error',
            filename='test.yml'
        )
        
        assert error.rule_id == 'E1001'
        assert error.message == 'Test error message'
        assert error.line_number == 10
        assert error.column_number == 5
        assert error.severity == 'error'
        assert error.filename == 'test.yml'
    
    def test_validation_result_creation(self):
        """Test ValidationResult data model creation."""
        template_path = Path('/tmp/test.yml')
        errors = [ValidationError('E1001', 'Test error', 10, 5, 'error')]
        warnings = [ValidationError('W2001', 'Test warning', 15, 3, 'warning')]
        
        result = ValidationResult(
            template_path=template_path,
            is_valid=False,
            errors=errors,
            warnings=warnings,
            execution_time=1.5
        )
        
        assert result.template_path == template_path
        assert result.is_valid == False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.execution_time == 1.5
    
    def test_validation_summary_creation(self):
        """Test ValidationSummary data model creation."""
        results = [
            ValidationResult(Path('/tmp/valid.yml'), True, [], [], 1.0),
            ValidationResult(Path('/tmp/invalid.yml'), False, [ValidationError('E1001', 'Error', 10, 5, 'error')], [], 1.5)
        ]
        
        summary = ValidationSummary(
            total_templates=2,
            valid_templates=1,
            failed_templates=1,
            total_errors=1,
            total_warnings=0,
            results=results,
            execution_time=2.5
        )
        
        assert summary.total_templates == 2
        assert summary.valid_templates == 1
        assert summary.failed_templates == 1
        assert summary.total_errors == 1
        assert summary.total_warnings == 0
        assert len(summary.results) == 2
        assert summary.execution_time == 2.5