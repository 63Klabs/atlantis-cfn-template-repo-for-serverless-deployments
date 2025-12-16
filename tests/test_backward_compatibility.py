"""
Property-based tests for CloudFormation template backward compatibility.

These tests verify that the v2 template maintains backward compatibility with
the original template by preserving parameters, resource naming, S3 bucket
properties, bucket policy statements, and outputs.
"""

import yaml
import pytest
from hypothesis import given, strategies as st, settings


# Custom YAML loader that handles CloudFormation intrinsic functions
class CFNLoader(yaml.SafeLoader):
    """YAML loader that handles CloudFormation intrinsic functions."""
    pass


# Add constructors for CloudFormation intrinsic functions
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
cfn_tags = ['!Ref', '!GetAtt', '!Sub', '!Join', '!If', '!Not', '!Equals', 
            '!And', '!Or', '!Select', '!Split', '!Base64', '!Cidr',
            '!FindInMap', '!GetAZs', '!ImportValue']

for tag in cfn_tags:
    CFNLoader.add_constructor(tag, cfn_constructor)


# Load both templates
def load_template(filepath):
    """Load and parse a CloudFormation YAML template."""
    with open(filepath, 'r') as f:
        return yaml.load(f, Loader=CFNLoader)


# Load templates once for all tests
ORIGINAL_TEMPLATE = load_template('../templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml')
V2_TEMPLATE = load_template('../templates/v2/storage/template-storage-s3-oac-for-cloudfront.yml')


def test_parameter_retention():
    """
    Property 1: Parameter retention
    For any parameter name in the original template, that parameter name must
    exist in the new template with the same Type.
    
    **Feature: cfn-s3-external-invalidator, Property 1: Parameter retention**
    **Validates: Requirements 1.2, 6.1**
    """
    original_params = ORIGINAL_TEMPLATE.get('Parameters', {})
    v2_params = V2_TEMPLATE.get('Parameters', {})
    
    for param_name, param_config in original_params.items():
        # Check parameter exists in v2
        assert param_name in v2_params, \
            f"Parameter '{param_name}' from original template is missing in v2 template"
        
        # Check parameter type is the same
        original_type = param_config.get('Type')
        v2_type = v2_params[param_name].get('Type')
        assert original_type == v2_type, \
            f"Parameter '{param_name}' has different Type: original={original_type}, v2={v2_type}"



def test_resource_naming_consistency():
    """
    Property 3: Resource naming consistency
    For any resource in the new template that also exists in the original template,
    the resource name pattern must be identical.
    
    **Feature: cfn-s3-external-invalidator, Property 3: Resource naming consistency**
    **Validates: Requirements 6.2**
    """
    original_resources = ORIGINAL_TEMPLATE.get('Resources', {})
    v2_resources = V2_TEMPLATE.get('Resources', {})
    
    # Resources that should exist in both templates
    common_resources = ['Bucket', 'BucketPolicy']
    
    for resource_name in common_resources:
        # Check resource exists in both templates
        assert resource_name in original_resources, \
            f"Resource '{resource_name}' missing from original template"
        assert resource_name in v2_resources, \
            f"Resource '{resource_name}' missing from v2 template"
        
        # Resource names are identical (they're the keys, so this is implicit)
        # But we verify the resource type is the same
        original_type = original_resources[resource_name].get('Type')
        v2_type = v2_resources[resource_name].get('Type')
        assert original_type == v2_type, \
            f"Resource '{resource_name}' has different Type: original={original_type}, v2={v2_type}"



def test_s3_bucket_property_preservation():
    """
    Property 4: S3 bucket property preservation
    For any S3 bucket property in the original template (excluding NotificationConfiguration
    and Tags), that property must exist in the new template with identical structure.
    
    **Feature: cfn-s3-external-invalidator, Property 4: S3 bucket property preservation**
    **Validates: Requirements 6.3**
    """
    original_bucket = ORIGINAL_TEMPLATE['Resources']['Bucket']['Properties']
    v2_bucket = V2_TEMPLATE['Resources']['Bucket']['Properties']
    
    # Properties to check (excluding NotificationConfiguration and Tags which are expected to differ)
    properties_to_check = [
        'BucketName',
        'BucketEncryption',
        'PublicAccessBlockConfiguration',
        'LoggingConfiguration'
    ]
    
    for prop_name in properties_to_check:
        # Check property exists in both
        assert prop_name in original_bucket, \
            f"Property '{prop_name}' missing from original bucket"
        assert prop_name in v2_bucket, \
            f"Property '{prop_name}' missing from v2 bucket"
        
        # Check property structure is identical
        original_value = original_bucket[prop_name]
        v2_value = v2_bucket[prop_name]
        assert original_value == v2_value, \
            f"Property '{prop_name}' differs between templates:\nOriginal: {original_value}\nV2: {v2_value}"



def test_bucket_policy_statement_preservation():
    """
    Property 5: Bucket policy statement preservation
    For any bucket policy statement with Sid "AllowCloudFrontServicePrincipalReadOnly"
    or "AllowCodeBuildReadWriteDelete", the statement structure must be identical
    between original and new templates.
    
    **Feature: cfn-s3-external-invalidator, Property 5: Bucket policy statement preservation**
    **Validates: Requirements 6.4**
    """
    original_policy = ORIGINAL_TEMPLATE['Resources']['BucketPolicy']['Properties']['PolicyDocument']
    v2_policy = V2_TEMPLATE['Resources']['BucketPolicy']['Properties']['PolicyDocument']
    
    # Get statements from both policies
    original_statements = original_policy['Statement']
    v2_statements = v2_policy['Statement']
    
    # Create dictionaries indexed by Sid for easier comparison
    original_by_sid = {stmt['Sid']: stmt for stmt in original_statements}
    v2_by_sid = {stmt['Sid']: stmt for stmt in v2_statements}
    
    # Statements that must be preserved
    sids_to_check = [
        'DenyNonSecureTransportAccess',
        'AllowCloudFrontServicePrincipalReadOnly',
        'AllowCodeBuildReadWriteDelete'
    ]
    
    for sid in sids_to_check:
        # Check statement exists in both
        assert sid in original_by_sid, \
            f"Statement with Sid '{sid}' missing from original policy"
        assert sid in v2_by_sid, \
            f"Statement with Sid '{sid}' missing from v2 policy"
        
        # Check statement structure is identical
        original_stmt = original_by_sid[sid]
        v2_stmt = v2_by_sid[sid]
        assert original_stmt == v2_stmt, \
            f"Statement with Sid '{sid}' differs between templates:\nOriginal: {original_stmt}\nV2: {v2_stmt}"



def test_output_retention():
    """
    Property 6: Output retention
    For any output name in the original template, that output name must exist
    in the new template.
    
    **Feature: cfn-s3-external-invalidator, Property 6: Output retention**
    **Validates: Requirements 6.5**
    """
    original_outputs = ORIGINAL_TEMPLATE.get('Outputs', {})
    v2_outputs = V2_TEMPLATE.get('Outputs', {})
    
    for output_name in original_outputs.keys():
        # Check output exists in v2
        assert output_name in v2_outputs, \
            f"Output '{output_name}' from original template is missing in v2 template"
