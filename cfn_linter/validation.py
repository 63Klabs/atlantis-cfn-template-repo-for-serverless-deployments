"""
CloudFormation Validation Engine for CFN Template Linter.
Executes cfn-lint validation on discovered templates and aggregates results.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import time
import logging
import os

from .venv_manager import VirtualEnvManager
from .environment import EnvironmentManager


@dataclass
class ValidationError:
    """Represents a validation error or warning from cfn-lint."""
    rule_id: str
    message: str
    line_number: Optional[int]
    column_number: Optional[int]
    severity: str  # 'error' or 'warning'
    filename: Optional[str] = None


@dataclass
class ValidationResult:
    """Represents the validation result for a single template."""
    template_path: Path
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    execution_time: float


@dataclass
class ValidationSummary:
    """Represents the aggregated validation results for all templates."""
    total_templates: int
    valid_templates: int
    failed_templates: int
    total_errors: int
    total_warnings: int
    results: List[ValidationResult]
    execution_time: float


class CFNValidator:
    """Validates CloudFormation templates using cfn-lint."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the CFN validator.
        
        Args:
            project_root: Path to project root. If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()
        self.venv_manager = VirtualEnvManager(project_root)
        self.env_manager = EnvironmentManager(project_root)
        
        # Set up logging for error tracking
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.WARNING)
    
    def validate_template(self, template_path: Path) -> ValidationResult:
        """Validate a single CloudFormation template.
        
        Args:
            template_path: Path to the CloudFormation template file.
            
        Returns:
            ValidationResult containing validation status and any errors/warnings.
        """
        start_time = time.time()
        
        # Pre-validation checks for file access errors
        try:
            if not template_path.exists():
                execution_time = time.time() - start_time
                self.logger.warning(f"Template file does not exist: {template_path}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='FILE_NOT_FOUND',
                        message=f'Template file does not exist: {template_path}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
            
            if not template_path.is_file():
                execution_time = time.time() - start_time
                self.logger.warning(f"Path is not a file: {template_path}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='NOT_A_FILE',
                        message=f'Path is not a file: {template_path}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
            
            # Check file permissions
            if not os.access(template_path, os.R_OK):
                execution_time = time.time() - start_time
                self.logger.warning(f"Cannot read template file (permission denied): {template_path}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='PERMISSION_DENIED',
                        message=f'Cannot read template file (permission denied): {template_path}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
            
            # Check if file is empty
            if template_path.stat().st_size == 0:
                execution_time = time.time() - start_time
                self.logger.warning(f"Template file is empty: {template_path}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='EMPTY_FILE',
                        message=f'Template file is empty: {template_path}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
            
            # Try to read the file to check for encoding issues
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read(1024)  # Read first 1KB to check readability
                    if not content.strip():
                        execution_time = time.time() - start_time
                        self.logger.warning(f"Template file appears to be empty or whitespace only: {template_path}")
                        return ValidationResult(
                            template_path=template_path,
                            is_valid=False,
                            errors=[ValidationError(
                                rule_id='EMPTY_CONTENT',
                                message=f'Template file appears to be empty or whitespace only: {template_path}',
                                line_number=None,
                                column_number=None,
                                severity='error'
                            )],
                            warnings=[],
                            execution_time=execution_time
                        )
            except UnicodeDecodeError as e:
                execution_time = time.time() - start_time
                self.logger.warning(f"Template file has encoding issues: {template_path} - {e}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='ENCODING_ERROR',
                        message=f'Template file has encoding issues: {e}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
            except IOError as e:
                execution_time = time.time() - start_time
                self.logger.warning(f"Cannot read template file: {template_path} - {e}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='FILE_READ_ERROR',
                        message=f'Cannot read template file: {e}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
                
        except OSError as e:
            execution_time = time.time() - start_time
            self.logger.warning(f"File system error accessing template: {template_path} - {e}")
            return ValidationResult(
                template_path=template_path,
                is_valid=False,
                errors=[ValidationError(
                    rule_id='FILESYSTEM_ERROR',
                    message=f'File system error accessing template: {e}',
                    line_number=None,
                    column_number=None,
                    severity='error'
                )],
                warnings=[],
                execution_time=execution_time
            )
        
        # Proceed with cfn-lint validation
        try:
            # Get cfn-lint executable path with error handling
            try:
                cfn_lint_path = self.venv_manager.get_cfn_lint_path()
            except Exception as e:
                execution_time = time.time() - start_time
                self.logger.error(f"Failed to get cfn-lint path: {e}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='CFN_LINT_SETUP_ERROR',
                        message=f'Failed to set up cfn-lint: {e}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
            
            # Run cfn-lint with JSON output format
            # Use environment-specific timeout
            timeout = self.env_manager.get_validation_timeout()
            
            try:
                result = subprocess.run(
                    [cfn_lint_path, "--format", "json", str(template_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=self.project_root  # Set working directory
                )
            except FileNotFoundError:
                execution_time = time.time() - start_time
                self.logger.error(f"cfn-lint executable not found at: {cfn_lint_path}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='CFN_LINT_NOT_FOUND',
                        message=f'cfn-lint executable not found at: {cfn_lint_path}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
            except PermissionError:
                execution_time = time.time() - start_time
                self.logger.error(f"Permission denied executing cfn-lint: {cfn_lint_path}")
                return ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='CFN_LINT_PERMISSION_ERROR',
                        message=f'Permission denied executing cfn-lint: {cfn_lint_path}',
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=execution_time
                )
            
            execution_time = time.time() - start_time
            
            # Parse cfn-lint output
            errors = []
            warnings = []
            
            if result.stdout:
                try:
                    lint_results = json.loads(result.stdout)
                    
                    for lint_error in lint_results:
                        validation_error = ValidationError(
                            rule_id=lint_error.get('Rule', {}).get('Id', 'Unknown'),
                            message=lint_error.get('Message', 'Unknown error'),
                            line_number=lint_error.get('Location', {}).get('Start', {}).get('LineNumber'),
                            column_number=lint_error.get('Location', {}).get('Start', {}).get('ColumnNumber'),
                            severity=lint_error.get('Level', 'error').lower(),
                            filename=lint_error.get('Filename')
                        )
                        
                        if validation_error.severity == 'warning':
                            warnings.append(validation_error)
                        else:
                            errors.append(validation_error)
                            
                except json.JSONDecodeError as e:
                    # If JSON parsing fails, treat as a general error
                    self.logger.warning(f"Failed to parse cfn-lint JSON output for {template_path}: {e}")
                    errors.append(ValidationError(
                        rule_id='JSON_PARSE_ERROR',
                        message=f'Failed to parse cfn-lint output: {result.stdout[:200]}...' if len(result.stdout) > 200 else result.stdout,
                        line_number=None,
                        column_number=None,
                        severity='error'
                    ))
            
            # Check if validation passed (no errors, warnings are okay)
            # cfn-lint returns non-zero for warnings too, so we only check for errors
            is_valid = len(errors) == 0
            
            # If cfn-lint returned non-zero but no JSON output, create a general error
            if result.returncode != 0 and not result.stdout and result.stderr:
                self.logger.warning(f"cfn-lint execution failed for {template_path}: {result.stderr}")
                errors.append(ValidationError(
                    rule_id='CFN_LINT_ERROR',
                    message=f'cfn-lint execution failed: {result.stderr[:200]}...' if len(result.stderr) > 200 else result.stderr,
                    line_number=None,
                    column_number=None,
                    severity='error'
                ))
                is_valid = False
            
            return ValidationResult(
                template_path=template_path,
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                execution_time=execution_time
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            timeout = self.env_manager.get_validation_timeout()
            self.logger.warning(f"cfn-lint execution timed out for {template_path}")
            return ValidationResult(
                template_path=template_path,
                is_valid=False,
                errors=[ValidationError(
                    rule_id='TIMEOUT_ERROR',
                    message=f'cfn-lint execution timed out after {timeout} seconds',
                    line_number=None,
                    column_number=None,
                    severity='error'
                )],
                warnings=[],
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Unexpected error validating template {template_path}: {e}")
            return ValidationResult(
                template_path=template_path,
                is_valid=False,
                errors=[ValidationError(
                    rule_id='EXECUTION_ERROR',
                    message=f'Validation execution failed: {str(e)}',
                    line_number=None,
                    column_number=None,
                    severity='error'
                )],
                warnings=[],
                execution_time=execution_time
            )
    
    def validate_all_templates(self, template_paths: List[Path]) -> ValidationSummary:
        """Validate all provided CloudFormation templates.
        
        Args:
            template_paths: List of paths to CloudFormation template files.
            
        Returns:
            ValidationSummary containing aggregated validation results.
        """
        start_time = time.time()
        
        results = []
        valid_count = 0
        failed_count = 0
        total_errors = 0
        total_warnings = 0
        processing_errors = []  # Track errors that occur during processing
        
        # Handle empty template list
        if not template_paths:
            self.logger.info("No templates provided for validation")
            execution_time = time.time() - start_time
            return ValidationSummary(
                total_templates=0,
                valid_templates=0,
                failed_templates=0,
                total_errors=0,
                total_warnings=0,
                results=[],
                execution_time=execution_time
            )
        
        self.logger.info(f"Starting validation of {len(template_paths)} templates")
        
        for i, template_path in enumerate(template_paths):
            try:
                self.logger.debug(f"Validating template {i+1}/{len(template_paths)}: {template_path}")
                
                result = self.validate_template(template_path)
                results.append(result)
                
                if result.is_valid:
                    valid_count += 1
                    self.logger.debug(f"Template validation successful: {template_path}")
                else:
                    failed_count += 1
                    self.logger.debug(f"Template validation failed: {template_path} - {len(result.errors)} errors")
                
                total_errors += len(result.errors)
                total_warnings += len(result.warnings)
                
            except Exception as e:
                # Handle individual template validation failures gracefully
                # This is a safety net - the validate_template method should handle most errors
                error_msg = f'Unexpected error during template validation: {str(e)}'
                self.logger.error(f"Unexpected error validating {template_path}: {e}")
                processing_errors.append(f"Template {template_path}: {error_msg}")
                
                failed_result = ValidationResult(
                    template_path=template_path,
                    is_valid=False,
                    errors=[ValidationError(
                        rule_id='VALIDATION_PROCESSING_ERROR',
                        message=error_msg,
                        line_number=None,
                        column_number=None,
                        severity='error'
                    )],
                    warnings=[],
                    execution_time=0.0
                )
                results.append(failed_result)
                failed_count += 1
                total_errors += 1
        
        execution_time = time.time() - start_time
        
        # Log processing summary
        if processing_errors:
            self.logger.warning(f"Encountered {len(processing_errors)} processing errors during validation")
            for error in processing_errors:
                self.logger.warning(f"Processing error: {error}")
        
        self.logger.info(f"Validation completed: {valid_count} valid, {failed_count} failed, "
                        f"{total_errors} total errors, {total_warnings} total warnings, "
                        f"execution time: {execution_time:.2f}s")
        
        return ValidationSummary(
            total_templates=len(template_paths),
            valid_templates=valid_count,
            failed_templates=failed_count,
            total_errors=total_errors,
            total_warnings=total_warnings,
            results=results,
            execution_time=execution_time
        )
    
    def format_validation_summary(self, summary: ValidationSummary) -> str:
        """Format validation summary for human-readable output.
        
        Args:
            summary: ValidationSummary to format.
            
        Returns:
            Formatted string representation of the validation summary.
        """
        lines = []
        lines.append("CloudFormation Template Validation Summary")
        lines.append("=" * 45)
        lines.append(f"Total templates processed: {summary.total_templates}")
        lines.append(f"Valid templates: {summary.valid_templates}")
        lines.append(f"Failed templates: {summary.failed_templates}")
        lines.append(f"Total errors: {summary.total_errors}")
        lines.append(f"Total warnings: {summary.total_warnings}")
        lines.append(f"Execution time: {summary.execution_time:.2f} seconds")
        
        # Add success rate
        if summary.total_templates > 0:
            success_rate = (summary.valid_templates / summary.total_templates) * 100
            lines.append(f"Success rate: {success_rate:.1f}%")
        
        lines.append("")
        
        # Handle case where no templates were processed
        if summary.total_templates == 0:
            lines.append("No templates were found or processed.")
            lines.append("Please check that CloudFormation template files exist in the specified directory.")
            return "\n".join(lines)
        
        # Show successful templates summary if any
        if summary.valid_templates > 0:
            lines.append(f"Successfully Validated Templates ({summary.valid_templates}):")
            lines.append("-" * 35)
            
            for result in summary.results:
                if result.is_valid:
                    warning_count = len(result.warnings)
                    warning_text = f" ({warning_count} warnings)" if warning_count > 0 else ""
                    lines.append(f"  ✓ {result.template_path}{warning_text}")
            
            lines.append("")
        
        # Show failed templates with detailed error information
        if summary.failed_templates > 0:
            lines.append(f"Failed Templates ({summary.failed_templates}):")
            lines.append("-" * 25)
            
            # Group errors by type for better aggregation
            error_types = {}
            
            for result in summary.results:
                if not result.is_valid:
                    lines.append(f"\n✗ {result.template_path}")
                    lines.append(f"  Errors: {len(result.errors)}, Warnings: {len(result.warnings)}")
                    
                    for error in result.errors:
                        location = ""
                        if error.line_number:
                            location = f" (line {error.line_number}"
                            if error.column_number:
                                location += f", col {error.column_number}"
                            location += ")"
                        
                        lines.append(f"    ERROR [{error.rule_id}]: {error.message}{location}")
                        
                        # Track error types for aggregation
                        if error.rule_id not in error_types:
                            error_types[error.rule_id] = 0
                        error_types[error.rule_id] += 1
                    
                    for warning in result.warnings:
                        location = ""
                        if warning.line_number:
                            location = f" (line {warning.line_number}"
                            if warning.column_number:
                                location += f", col {warning.column_number}"
                            location += ")"
                        
                        lines.append(f"    WARNING [{warning.rule_id}]: {warning.message}{location}")
            
            # Add error type aggregation summary
            if error_types:
                lines.append("")
                lines.append("Error Summary by Type:")
                lines.append("-" * 25)
                
                # Sort by frequency (most common first)
                sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
                
                for rule_id, count in sorted_errors:
                    lines.append(f"  {rule_id}: {count} occurrence{'s' if count != 1 else ''}")
        
        # Add recommendations if there are failures
        if summary.failed_templates > 0:
            lines.append("")
            lines.append("Recommendations:")
            lines.append("-" * 15)
            lines.append("• Review the error messages above for specific issues to fix")
            lines.append("• Check CloudFormation template syntax and resource definitions")
            lines.append("• Ensure all required properties are specified for each resource")
            lines.append("• Verify resource types are valid and supported by AWS")
            lines.append("• Consider using AWS CloudFormation documentation for reference")
        
        return "\n".join(lines)
    
    def get_error_aggregation_report(self, summary: ValidationSummary) -> dict:
        """Generate an error aggregation report for programmatic use.
        
        Args:
            summary: ValidationSummary to analyze.
            
        Returns:
            Dictionary containing aggregated error information.
        """
        report = {
            'total_templates': summary.total_templates,
            'valid_templates': summary.valid_templates,
            'failed_templates': summary.failed_templates,
            'total_errors': summary.total_errors,
            'total_warnings': summary.total_warnings,
            'success_rate': (summary.valid_templates / summary.total_templates * 100) if summary.total_templates > 0 else 0,
            'error_types': {},
            'warning_types': {},
            'failed_template_paths': [],
            'processing_errors': []
        }
        
        for result in summary.results:
            if not result.is_valid:
                report['failed_template_paths'].append(str(result.template_path))
                
                # Aggregate error types
                for error in result.errors:
                    rule_id = error.rule_id
                    if rule_id not in report['error_types']:
                        report['error_types'][rule_id] = {
                            'count': 0,
                            'templates': [],
                            'sample_message': error.message
                        }
                    report['error_types'][rule_id]['count'] += 1
                    if str(result.template_path) not in report['error_types'][rule_id]['templates']:
                        report['error_types'][rule_id]['templates'].append(str(result.template_path))
                
                # Aggregate warning types
                for warning in result.warnings:
                    rule_id = warning.rule_id
                    if rule_id not in report['warning_types']:
                        report['warning_types'][rule_id] = {
                            'count': 0,
                            'templates': [],
                            'sample_message': warning.message
                        }
                    report['warning_types'][rule_id]['count'] += 1
                    if str(result.template_path) not in report['warning_types'][rule_id]['templates']:
                        report['warning_types'][rule_id]['templates'].append(str(result.template_path))
        
        return report