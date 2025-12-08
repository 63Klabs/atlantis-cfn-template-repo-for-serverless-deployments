"""
Property-based tests for CloudFormation template ARN pattern validation.

**Feature: cfn-s3-external-invalidator, Property 2: ARN pattern validation**
**Validates: Requirements 2.4**
"""

import re
import pytest
from hypothesis import given, strategies as st, settings


# The ARN pattern from the CloudFormation template
ARN_PATTERN = r"^$|^arn:aws:(lambda|sqs|states|sns):[a-z0-9-]+:\d{12}:(function|queue|stateMachine|topic)\/[a-zA-Z0-9-_]+$"


# Strategy for generating valid AWS regions
valid_regions = st.sampled_from([
    'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
    'eu-west-1', 'eu-west-2', 'eu-central-1',
    'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1'
])

# Strategy for generating valid AWS account IDs (12 digits)
valid_account_ids = st.text(min_size=12, max_size=12, alphabet='0123456789')

# Strategy for generating valid resource names
valid_resource_names = st.text(
    min_size=1,
    max_size=64,
    alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_'
)

# Service configurations: (service_name, resource_type)
service_configs = [
    ('lambda', 'function'),
    ('sqs', 'queue'),
    ('states', 'stateMachine'),
    ('sns', 'topic')
]


@st.composite
def valid_arns(draw):
    """Generate valid ARNs for Lambda, SQS, Step Functions, and SNS."""
    service, resource_type = draw(st.sampled_from(service_configs))
    region = draw(valid_regions)
    account_id = draw(valid_account_ids)
    resource_name = draw(valid_resource_names)
    
    return f"arn:aws:{service}:{region}:{account_id}:{resource_type}/{resource_name}"


@st.composite
def invalid_arns(draw):
    """Generate invalid ARNs that should be rejected."""
    invalid_type = draw(st.sampled_from([
        'wrong_service',
        'wrong_region',
        'wrong_account',
        'wrong_resource_type',
        'wrong_format',
        'missing_parts'
    ]))
    
    if invalid_type == 'wrong_service':
        # Invalid service name
        region = draw(valid_regions)
        account_id = draw(valid_account_ids)
        resource_name = draw(valid_resource_names)
        return f"arn:aws:ec2:{region}:{account_id}:instance/{resource_name}"
    
    elif invalid_type == 'wrong_region':
        # Invalid region format (contains uppercase or invalid characters)
        service, resource_type = draw(st.sampled_from(service_configs))
        account_id = draw(valid_account_ids)
        resource_name = draw(valid_resource_names)
        return f"arn:aws:{service}:US-EAST-1:{account_id}:{resource_type}/{resource_name}"
    
    elif invalid_type == 'wrong_account':
        # Invalid account ID (not 12 digits)
        service, resource_type = draw(st.sampled_from(service_configs))
        region = draw(valid_regions)
        resource_name = draw(valid_resource_names)
        invalid_account = draw(st.sampled_from(['123', '12345678901234', 'abcd12345678']))
        return f"arn:aws:{service}:{region}:{invalid_account}:{resource_type}/{resource_name}"
    
    elif invalid_type == 'wrong_resource_type':
        # Invalid resource type
        service, _ = draw(st.sampled_from(service_configs))
        region = draw(valid_regions)
        account_id = draw(valid_account_ids)
        resource_name = draw(valid_resource_names)
        return f"arn:aws:{service}:{region}:{account_id}:invalid-type/{resource_name}"
    
    elif invalid_type == 'wrong_format':
        # Wrong separator (using : instead of /)
        service, resource_type = draw(st.sampled_from(service_configs))
        region = draw(valid_regions)
        account_id = draw(valid_account_ids)
        resource_name = draw(valid_resource_names)
        return f"arn:aws:{service}:{region}:{account_id}:{resource_type}:{resource_name}"
    
    else:  # missing_parts
        # Missing parts of the ARN
        return draw(st.sampled_from([
            'arn:aws:lambda',
            'arn:aws:lambda:us-east-1',
            'arn:aws:lambda:us-east-1:123456789012',
            'not-an-arn-at-all'
        ]))


@settings(max_examples=100)
@given(arn=valid_arns())
def test_valid_arns_are_accepted(arn):
    """
    Property: For any valid Lambda, SQS, Step Functions, or SNS ARN,
    the InvalidatorArn parameter's AllowedPattern regex must accept it.
    
    **Feature: cfn-s3-external-invalidator, Property 2: ARN pattern validation**
    **Validates: Requirements 2.4**
    """
    pattern = re.compile(ARN_PATTERN)
    assert pattern.match(arn) is not None, f"Valid ARN was rejected: {arn}"


@settings(max_examples=100)
@given(arn=invalid_arns())
def test_invalid_arns_are_rejected(arn):
    """
    Property: For any invalid ARN format,
    the InvalidatorArn parameter's AllowedPattern regex must reject it.
    
    **Feature: cfn-s3-external-invalidator, Property 2: ARN pattern validation**
    **Validates: Requirements 2.4**
    """
    pattern = re.compile(ARN_PATTERN)
    assert pattern.match(arn) is None, f"Invalid ARN was accepted: {arn}"


def test_empty_string_is_accepted():
    """
    Unit test: Empty string should be accepted (allows disabling invalidation).
    
    **Feature: cfn-s3-external-invalidator, Property 2: ARN pattern validation**
    **Validates: Requirements 2.4**
    """
    pattern = re.compile(ARN_PATTERN)
    assert pattern.match("") is not None, "Empty string should be accepted"


# Specific examples for each service type
@pytest.mark.parametrize("arn,expected", [
    # Valid Lambda ARNs
    ("arn:aws:lambda:us-east-1:123456789012:function/my-function", True),
    ("arn:aws:lambda:eu-west-1:999999999999:function/test_func-123", True),
    
    # Valid SQS ARNs
    ("arn:aws:sqs:us-west-2:123456789012:queue/my-queue", True),
    ("arn:aws:sqs:ap-southeast-1:111111111111:queue/test-queue_123", True),
    
    # Valid Step Functions ARNs
    ("arn:aws:states:us-east-1:123456789012:stateMachine/my-state-machine", True),
    ("arn:aws:states:eu-central-1:222222222222:stateMachine/workflow_123", True),
    
    # Valid SNS ARNs
    ("arn:aws:sns:us-east-1:123456789012:topic/my-topic", True),
    ("arn:aws:sns:ap-northeast-1:333333333333:topic/notifications-123", True),
    
    # Invalid ARNs
    ("arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0", False),
    ("arn:aws:lambda:US-EAST-1:123456789012:function/my-function", False),
    ("arn:aws:lambda:us-east-1:12345:function/my-function", False),
    ("arn:aws:lambda:us-east-1:123456789012:invalid/my-function", False),
    ("not-an-arn", False),
    ("arn:aws:lambda", False),
])
def test_specific_arn_examples(arn, expected):
    """
    Unit test: Specific ARN examples to verify correct behavior.
    
    **Feature: cfn-s3-external-invalidator, Property 2: ARN pattern validation**
    **Validates: Requirements 2.4**
    """
    pattern = re.compile(ARN_PATTERN)
    result = pattern.match(arn) is not None
    assert result == expected, f"ARN '{arn}' - expected {expected}, got {result}"
