#!/usr/bin/env python3

VERSION = "v0.1.0/2025-01-25"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer
# https://chadkluck.me

# Install:
# pip install -r requirements.txt
# -- OR --
# pip install boto3
# -- OR --
# Create and activate virtual environment
# python -m venv venv
# source venv/bin/activate  # On Linux/Mac
# pip install -r requirements.txt

# Make Executable:
# chmod +x s3_inventory.py

# Basic usage
# ./s3_inventory.py my-bucket-name

# With specific AWS profile
# ./s3_inventory.py my-bucket-name --profile myprofile

# With custom output directory
# ./s3_inventory.py my-bucket-name --output-dir /path/to/output

import boto3
import json
import csv
import os
import argparse
from botocore.exceptions import ClientError, ProfileNotFound
from collections import defaultdict
from datetime import datetime, UTC

def setup_aws_client(profile=None):
    """Configure AWS client with optional profile"""
    try:
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        return session.client('s3')
    except ProfileNotFound:
        raise Exception(f"AWS profile '{profile}' not found")

def create_output_directory(directory):
    """Create output directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def check_bucket_access(s3_client, bucket):
    """Verify bucket exists and we have access"""
    try:
        s3_client.head_bucket(Bucket=bucket)
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404':
            raise Exception(f"Bucket '{bucket}' does not exist")
        elif error_code == '403':
            raise Exception(f"Permission denied for bucket '{bucket}'")
        else:
            raise Exception(f"Error accessing bucket: {str(e)}")

def generate_summary(versions, delete_markers, bucket, summary_file):
    """Generate and write summary statistics"""
    unique_objects = len(set(v['Key'] for v in versions))
    total_size = sum(v.get('Size', 0) for v in versions)
    total_size_gb = total_size / (1024**3)
    
    # Count storage classes
    storage_classes = {}
    for v in versions:
        storage_class = v.get('StorageClass', 'Standard')
        storage_classes[storage_class] = storage_classes.get(storage_class, 0) + 1
    
    with open(summary_file, 'w') as f:
        f.write("S3 Bucket Inventory Summary\n")
        f.write("-" * 40 + "\n")
        f.write(f"Bucket: {bucket}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write("-" * 40 + "\n\n")
        f.write(f"Total Objects (including versions): {len(versions)}\n")
        f.write(f"Total Delete Markers: {len(delete_markers)}\n")
        f.write(f"Unique Objects: {unique_objects}\n")
        f.write(f"Total Size: {total_size_gb:.2f} GB\n\n")
        
        f.write("Storage Class Distribution:\n")
        for sc, count in storage_classes.items():
            f.write(f"{sc}: {count}\n")

def get_bucket_inventory(s3_client, bucket, prefix=''):
    """Retrieve all objects and their versions from the bucket under specified prefix"""
    try:
        versions = []
        delete_markers = []
        
        # Get bucket region
        region = s3_client.get_bucket_location(Bucket=bucket)['LocationConstraint']
        if region is None:
            region = 'us-east-1'
        
        paginator = s3_client.get_paginator('list_object_versions')
        
        # Add prefix to pagination parameters if provided
        params = {'Bucket': bucket}
        if prefix:
            # Ensure prefix ends with / if provided
            prefix = prefix.rstrip('/') + '/' if prefix else ''
            params['Prefix'] = prefix
        
        for page in paginator.paginate(**params):
            # Process object versions
            if 'Versions' in page:
                for version in page['Versions']:
                    version['Bucket'] = bucket
                    version['Region'] = region
                versions.extend(page['Versions'])
            
            # Process delete markers
            if 'DeleteMarkers' in page:
                for marker in page['DeleteMarkers']:
                    marker['Bucket'] = bucket
                    marker['Region'] = region
                delete_markers.extend(page['DeleteMarkers'])
                
        return versions, delete_markers
    
    except ClientError as e:
        raise Exception(f"Error listing bucket contents: {str(e)}")

def write_inventory_csv(versions, delete_markers, output_file):
    """Write inventory data to CSV file"""
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'File Path', 
            'Size (Bytes)', 
            'Last Modified', 
            'Version ID', 
            'Storage Class',
            'S3 URI',
            'HTTP URI',
            'ETag'
        ])
        
        # Write versions
        for v in versions:
            s3_uri = f"s3://{v['Bucket']}/{v['Key']}"
            if v.get('VersionId'):
                s3_uri += f"?versionId={v['VersionId']}"
            
            http_uri = f"https://{v['Bucket']}.s3.{v['Region']}.amazonaws.com/{v['Key']}"
            if v.get('VersionId'):
                http_uri += f"?versionId={v['VersionId']}"
            
            writer.writerow([
                v['Key'],
                v.get('Size', 0),
                v['LastModified'].isoformat(),
                v.get('VersionId', '-'),
                v.get('StorageClass', '-'),
                s3_uri,
                http_uri,
                v.get('ETag', '-')
            ])
        
        # Write delete markers
        for dm in delete_markers:
            s3_uri = f"s3://{dm['Bucket']}/{dm['Key']}"
            if dm.get('VersionId'):
                s3_uri += f"?versionId={dm['VersionId']}"
            
            http_uri = f"https://{dm['Bucket']}.s3.{dm['Region']}.amazonaws.com/{dm['Key']}"
            if dm.get('VersionId'):
                http_uri += f"?versionId={dm['VersionId']}"
            
            writer.writerow([
                dm['Key'],
                0,
                dm['LastModified'].isoformat(),
                dm.get('VersionId', '-'),
                'DeleteMarker',
                s3_uri,
                http_uri,
                dm.get('ETag', '-')
            ])
def process_objects(versions, delete_markers):
    """
    Process versions and delete markers into a common data structure
    Returns a defaultdict with sorted versions for each object, excluding any objects with delete markers
    """
    objects = defaultdict(list)
    deleted_keys = {dm['Key'] for dm in delete_markers}  # Set of keys that have delete markers
    
    # Only process versions for keys that don't have delete markers
    for item in versions:
        key = item['Key']
        
        # Skip if this key has any delete markers
        if key in deleted_keys:
            continue
            
        version_id = item.get('VersionId')
        base_uri = f"s3://{item['Bucket']}/{key}"
        versioned_uri = f"{base_uri}?versionId={version_id}" if version_id else base_uri
        
        objects[key].append({
            'uri': versioned_uri,
            'base_uri': base_uri,
            'bucket': item['Bucket'],
            'key': key,
            'version_id': version_id,
            'size': item.get('Size', 0),
            'last_modified': item['LastModified'],
            'storage_class': item.get('StorageClass'),
            'e_tag': item.get('ETag')
        })
    
    # Sort versions for each object by last_modified date
    for versions in objects.values():
        versions.sort(key=lambda x: x['last_modified'])
    
    return objects

def generate_json_inventory(objects, json_file):
    """Generate JSON inventory from processed objects"""
    inventory = {
        'generated_at': datetime.now(UTC).isoformat(),
        'objects': {}
    }
    
    # Convert defaultdict to regular dict for JSON serialization
    for key, versions in sorted(objects.items()):
        inventory['objects'][key] = [
            {k: v.isoformat() if isinstance(v, datetime) else v 
                for k, v in version.items()}
            for version in versions
        ]
    
    with open(json_file, 'w') as f:
        json.dump(inventory, f, indent=2)

def generate_text_inventory(objects, text_file):
    """Generate text inventory from processed objects"""
    with open(text_file, 'w') as f:
        f.write("S3 URI Inventory\n")
        f.write("=" * 80 + "\n\n")
        
        # Write base URIs without versions
        f.write("Base URIs (without versions):\n")
        f.write("-" * 80 + "\n")
        for key in sorted(objects.keys()):
            f.write(f"{objects[key][0]['base_uri']}\n")
        
        # Write versioned URIs with dates
        f.write("\nVersioned URIs with creation dates:\n")
        f.write("-" * 80 + "\n")
        for key in sorted(objects.keys()):
            for obj in objects[key]:
                f.write(f"{obj['uri']}\n")
                f.write(f"    Created: {obj['last_modified'].isoformat()}\n")

def main():
    parser = argparse.ArgumentParser(description='Generate S3 bucket inventory')
    parser.add_argument('bucket', help='Name of the S3 bucket')
    parser.add_argument('path', nargs='?', default='', help='Path prefix in the bucket to inventory (optional)')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--output-dir', default='outputs', help='Output directory for inventory files')
    args = parser.parse_args()

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Define all file paths before try block
    path = args.path.strip('/') + '/'
    path_suffix = path.replace('/', '_').rstrip('_') if args.path else 'full'
    inventory_file = os.path.join(args.output_dir, f's3_inventory_{path_suffix}_{timestamp}.csv')
    summary_file = os.path.join(args.output_dir, f's3_inventory_summary_{path_suffix}_{timestamp}.txt')
    error_log = os.path.join(args.output_dir, f's3_inventory_errors_{timestamp}.log')
    json_file = os.path.join(args.output_dir, f'inventory_{path_suffix}.json')
    text_file = os.path.join(args.output_dir, f'inventory_{path_suffix}.txt')

    try:
        # Create output directory
        create_output_directory(args.output_dir)
        
        # Setup AWS client
        s3_client = setup_aws_client(args.profile)
        
        # Check bucket access
        check_bucket_access(s3_client, args.bucket)
        
        print(f"Starting inventory of bucket: {args.bucket}")
        if args.path:
            print(f"Inventorying path: {path}")
        
        # Get bucket inventory
        versions, delete_markers = get_bucket_inventory(s3_client, args.bucket, path)
        
        if not versions and not delete_markers:
            print(f"No objects found in path: {path}")
            return 0
        
        # Write inventory to CSV
        write_inventory_csv(versions, delete_markers, inventory_file)
        
        # Generate summary
        generate_summary(versions, delete_markers, args.bucket, summary_file)
        
        # Process objects once
        processed_objects = process_objects(versions, delete_markers)

        # Generate both inventories using the processed data
        generate_json_inventory(processed_objects, json_file)
        generate_text_inventory(processed_objects, text_file)

        print("\nInventory complete!")
        print(f"Main inventory file: {inventory_file}")
        print(f"Summary file: {summary_file}")
        print(f"JSON inventory: {json_file}")
        print(f"Text inventory: {text_file}")

    except Exception as e:
        print(f"Error: {str(e)}")
        # Create output directory if it doesn't exist (might not have been created if error occurred early)
        create_output_directory(args.output_dir)
        with open(error_log, 'w') as f:
            f.write(f"Error occurred at {datetime.now().isoformat()}\n")
            f.write(str(e))
        print(f"Error details written to: {error_log}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
