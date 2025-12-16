"""
CloudFormation template validation utilities for testing.

This module provides helper functions for loading, parsing, and validating
CloudFormation templates, supporting both unit and property-based testing.
"""

import yaml
import re
from typing import Dict, Any, List, Optional, Union
from pathlib import Path


class CFNLoader(yaml.SafeLoader):
    """YAML loader that handles CloudFormation intrinsic functions."""
    pass


def cfn_constructor(loader, node):
    """Generic constructor for CloudFormation intrinsic functions."""
    if isinstance(node, yaml.ScalarNode):
        return {node.tag: loader.construct_scalar(node)}
    elif isinstance(node, yaml.SequenceNode):
        return {node.tag: loader.construct_sequence(node)}
    elif isinstance(node, yaml.MappingNode):
        return {node.tag: loader.construct_mapping(node)}
    return {node.tag: None}


# Register CloudFormation intrinsic functions
CFN_TAGS = [
    '!Ref', '!GetAtt', '!Sub', '!Join', '!If', '!Not', '!Equals', 
    '!And', '!Or', '!Select', '!Split', '!Base64', '!Cidr',
    '!FindInMap', '!GetAZs', '!ImportValue', '!Condition'
]

for tag in CFN_TAGS:
    CFNLoader.add_constructor(tag, cfn_constructor)


def load_template(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    Load and parse a CloudFormation YAML template.
    
    Args:
        filepath: Path to the CloudFormation template file
        
    Returns:
        Parsed template as a dictionary
        
    Raises:
        FileNotFoundError: If template file doesn't exist
        yaml.YAMLError: If template has invalid YAML syntax
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Template file not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.load(f, Loader=CFNLoader)


def get_template_section(template: Dict[str, Any], section: str) -> Dict[str, Any]:
    """
    Get a specific section from a CloudFormation template.
    
    Args:
        template: Parsed CloudFormation template
        section: Section name (e.g., 'Parameters', 'Resources', 'Conditions')
        
    Returns:
        Dictionary containing the requested section, empty dict if not found
    """
    return template.get(section, {})


def find_resources_by_type(template: Dict[str, Any], resource_type: str) -> Dict[str, Dict[str, Any]]:
    """
    Find all resources of a specific type in the template.
    
    Args:
        template: Parsed CloudFormation template
        resource_type: AWS resource type (e.g., 'AWS::CodeBuild::Project')
        
    Returns:
        Dictionary mapping resource names to resource definitions
    """
    resources = get_template_section(template, 'Resources')
    return {
        name: resource for name, resource in resources.items()
        if resource.get('Type') == resource_type
    }


def find_resources_with_condition(template: Dict[str, Any], condition_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Find all resources that use a specific condition.
    
    Args:
        template: Parsed CloudFormation template
        condition_name: Name of the condition to search for
        
    Returns:
        Dictionary mapping resource names to resource definitions
    """
    resources = get_template_section(template, 'Resources')
    matching_resources = {}
    
    for name, resource in resources.items():
        resource_condition = resource.get('Condition')
        if resource_condition == condition_name:
            matching_resources[name] = resource
        elif isinstance(resource_condition, dict):
            # Handle complex conditions
            condition_str = str(resource_condition)
            if condition_name in condition_str:
                matching_resources[name] = resource
    
    return matching_resources


def get_parameter_references(obj: Any, param_name: str) -> List[str]:
    """
    Recursively find all references to a parameter in a CloudFormation object.
    
    Args:
        obj: CloudFormation object (dict, list, or primitive)
        param_name: Parameter name to search for
        
    Returns:
        List of reference locations found
    """
    references = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == '!Ref' and value == param_name:
                references.append(f"!Ref {param_name}")
            else:
                references.extend(get_parameter_references(value, param_name))
    elif isinstance(obj, list):
        for item in obj:
            references.extend(get_parameter_references(item, param_name))
    elif isinstance(obj, str) and obj == param_name:
        references.append(obj)
    
    return references


def validate_parameter_constraints(template: Dict[str, Any], param_name: str) -> Dict[str, Any]:
    """
    Validate parameter constraints and return constraint information.
    
    Args:
        template: Parsed CloudFormation template
        param_name: Parameter name to validate
        
    Returns:
        Dictionary containing parameter constraint information
        
    Raises:
        KeyError: If parameter doesn't exist
    """
    parameters = get_template_section(template, 'Parameters')
    if param_name not in parameters:
        raise KeyError(f"Parameter '{param_name}' not found in template")
    
    param = parameters[param_name]
    constraints = {}
    
    # Extract common constraint types
    constraint_fields = [
        'Type', 'Default', 'AllowedValues', 'AllowedPattern',
        'MinLength', 'MaxLength', 'MinValue', 'MaxValue'
    ]
    
    for field in constraint_fields:
        if field in param:
            constraints[field] = param[field]
    
    return constraints


def validate_condition_logic(template: Dict[str, Any], condition_name: str) -> Dict[str, Any]:
    """
    Validate condition logic and return condition information.
    
    Args:
        template: Parsed CloudFormation template
        condition_name: Condition name to validate
        
    Returns:
        Dictionary containing condition structure information
        
    Raises:
        KeyError: If condition doesn't exist
    """
    conditions = get_template_section(template, 'Conditions')
    if condition_name not in conditions:
        raise KeyError(f"Condition '{condition_name}' not found in template")
    
    condition = conditions[condition_name]
    
    # Analyze condition structure
    analysis = {
        'condition_name': condition_name,
        'condition_def': condition,
        'type': None,
        'parameters_referenced': [],
        'conditions_referenced': []
    }
    
    # Determine condition type
    if isinstance(condition, dict):
        if '!Equals' in condition:
            analysis['type'] = 'Equals'
        elif '!And' in condition:
            analysis['type'] = 'And'
        elif '!Or' in condition:
            analysis['type'] = 'Or'
        elif '!Not' in condition:
            analysis['type'] = 'Not'
        elif '!Condition' in condition:
            analysis['type'] = 'ConditionRef'
    
    # Find parameter references
    condition_str = str(condition)
    template_params = get_template_section(template, 'Parameters')
    for param_name in template_params.keys():
        if param_name in condition_str:
            analysis['parameters_referenced'].append(param_name)
    
    # Find condition references
    template_conditions = get_template_section(template, 'Conditions')
    for cond_name in template_conditions.keys():
        if cond_name != condition_name and cond_name in condition_str:
            analysis['conditions_referenced'].append(cond_name)
    
    return analysis


def validate_iam_policy_structure(policy_document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate IAM policy document structure.
    
    Args:
        policy_document: IAM policy document
        
    Returns:
        Dictionary containing policy analysis
    """
    analysis = {
        'version': policy_document.get('Version'),
        'statements': [],
        'statement_count': 0,
        'actions': set(),
        'resources': set(),
        'effects': set()
    }
    
    statements = policy_document.get('Statement', [])
    if not isinstance(statements, list):
        statements = [statements]
    
    analysis['statement_count'] = len(statements)
    
    for i, statement in enumerate(statements):
        stmt_analysis = {
            'index': i,
            'sid': statement.get('Sid'),
            'effect': statement.get('Effect'),
            'actions': [],
            'resources': [],
            'conditions': statement.get('Condition')
        }
        
        # Extract actions
        actions = statement.get('Action', [])
        if isinstance(actions, str):
            actions = [actions]
        stmt_analysis['actions'] = actions
        analysis['actions'].update(actions)
        
        # Extract resources
        resources = statement.get('Resource', [])
        if isinstance(resources, str):
            resources = [resources]
        stmt_analysis['resources'] = resources
        analysis['resources'].update(str(r) for r in resources)
        
        # Track effects
        if stmt_analysis['effect']:
            analysis['effects'].add(stmt_analysis['effect'])
        
        analysis['statements'].append(stmt_analysis)
    
    return analysis


def validate_environment_variables(env_vars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate CodeBuild environment variables structure.
    
    Args:
        env_vars: List of environment variable definitions
        
    Returns:
        Dictionary containing environment variable analysis
    """
    analysis = {
        'variable_count': len(env_vars),
        'variables': {},
        'variable_names': set(),
        'parameter_references': set(),
        'hardcoded_values': set()
    }
    
    for env_var in env_vars:
        name = env_var.get('Name')
        value = env_var.get('Value')
        var_type = env_var.get('Type', 'PLAINTEXT')
        
        if name:
            analysis['variable_names'].add(name)
            analysis['variables'][name] = {
                'value': value,
                'type': var_type
            }
            
            # Analyze value type
            if isinstance(value, dict) and '!Ref' in value:
                analysis['parameter_references'].add(value['!Ref'])
            elif isinstance(value, str) and not any(func in str(value) for func in CFN_TAGS):
                analysis['hardcoded_values'].add(value)
    
    return analysis


def compare_resource_properties(resource1: Dict[str, Any], resource2: Dict[str, Any], 
                              properties_to_compare: List[str]) -> Dict[str, Any]:
    """
    Compare specific properties between two resources.
    
    Args:
        resource1: First resource definition
        resource2: Second resource definition
        properties_to_compare: List of property paths to compare (e.g., ['Environment.ComputeType'])
        
    Returns:
        Dictionary containing comparison results
    """
    comparison = {
        'matching_properties': [],
        'differing_properties': [],
        'missing_in_resource1': [],
        'missing_in_resource2': []
    }
    
    def get_nested_property(resource: Dict[str, Any], property_path: str) -> Any:
        """Get a nested property using dot notation."""
        keys = property_path.split('.')
        current = resource.get('Properties', {})
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    for prop_path in properties_to_compare:
        value1 = get_nested_property(resource1, prop_path)
        value2 = get_nested_property(resource2, prop_path)
        
        if value1 is None and value2 is None:
            continue
        elif value1 is None:
            comparison['missing_in_resource1'].append(prop_path)
        elif value2 is None:
            comparison['missing_in_resource2'].append(prop_path)
        elif value1 == value2:
            comparison['matching_properties'].append(prop_path)
        else:
            comparison['differing_properties'].append({
                'property': prop_path,
                'resource1_value': value1,
                'resource2_value': value2
            })
    
    return comparison


def validate_pipeline_stages(pipeline_resource: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate CodePipeline stages configuration.
    
    Args:
        pipeline_resource: CodePipeline resource definition
        
    Returns:
        Dictionary containing pipeline stage analysis
    """
    analysis = {
        'stage_count': 0,
        'stages': [],
        'stage_names': [],
        'conditional_stages': False,
        'postdeploy_stage_present': False
    }
    
    properties = pipeline_resource.get('Properties', {})
    stages = properties.get('Stages')
    
    if stages is None:
        return analysis
    
    # Handle conditional stages
    if isinstance(stages, dict) and '!If' in stages:
        analysis['conditional_stages'] = True
        if_condition = stages['!If']
        
        if len(if_condition) >= 2:
            # Analyze both branches
            stages_with_condition = if_condition[1] if len(if_condition) > 1 else []
            stages_without_condition = if_condition[2] if len(if_condition) > 2 else []
            
            # Check stages with condition
            for stage in stages_with_condition:
                stage_name = stage.get('Name', '')
                analysis['stage_names'].append(f"{stage_name} (conditional)")
                if stage_name == 'PostDeploy':
                    analysis['postdeploy_stage_present'] = True
            
            analysis['stage_count'] = len(stages_with_condition)
    elif isinstance(stages, list):
        # Direct stage list
        analysis['stage_count'] = len(stages)
        for stage in stages:
            stage_name = stage.get('Name', '')
            analysis['stage_names'].append(stage_name)
            if stage_name == 'PostDeploy':
                analysis['postdeploy_stage_present'] = True
    
    return analysis


def validate_regex_pattern(pattern: str, test_strings: List[str]) -> Dict[str, Any]:
    """
    Validate a regex pattern against test strings.
    
    Args:
        pattern: Regular expression pattern
        test_strings: List of strings to test against the pattern
        
    Returns:
        Dictionary containing validation results
    """
    try:
        compiled_pattern = re.compile(pattern)
    except re.error as e:
        return {
            'valid_pattern': False,
            'error': str(e),
            'matches': {},
            'match_count': 0
        }
    
    results = {
        'valid_pattern': True,
        'pattern': pattern,
        'matches': {},
        'match_count': 0,
        'matching_strings': [],
        'non_matching_strings': []
    }
    
    for test_string in test_strings:
        match = compiled_pattern.match(test_string)
        results['matches'][test_string] = match is not None
        
        if match:
            results['matching_strings'].append(test_string)
            results['match_count'] += 1
        else:
            results['non_matching_strings'].append(test_string)
    
    return results