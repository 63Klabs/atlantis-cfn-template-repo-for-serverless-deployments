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
from datetime import datetime
from botocore.exceptions import ClientError, ProfileNotFound
from collections import defaultdict

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
                versions.extend(page['Versions'])
            
            # Process delete markers
            if 'DeleteMarkers' in page:
                delete_markers.extend(page['DeleteMarkers'])
                
        return versions, delete_markers
    
    except ClientError as e:
        raise Exception(f"Error listing bucket contents: {str(e)}")

def write_inventory_csv(versions, delete_markers, output_file):
    """Write inventory data to CSV file"""
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['File Path', 'Size (Bytes)', 'Last Modified', 'Version ID', 'Storage Class'])
        
        # Write versions
        for v in versions:
            writer.writerow([
                v['Key'],
                v.get('Size', 0),
                v['LastModified'].isoformat(),
                v.get('VersionId', '-'),
                v.get('StorageClass', '-')
            ])
        
        # Write delete markers
        for dm in delete_markers:
            writer.writerow([
                dm['Key'],
                0,
                dm['LastModified'].isoformat(),
                dm.get('VersionId', '-'),
                'DeleteMarker'
            ])

def generate_json_inventory(versions, delete_markers, json_file):
    """Generate JSON inventory with grouped file paths and their versions"""
    # Create a defaultdict to group versions by key
    inventory = defaultdict(lambda: {
        "versions": [],
        "total_versions": 0,
        "latest_version": None,
        "total_size": 0,
        "has_delete_markers": False
    })
    
    # Process versions
    for v in versions:
        key = v['Key']
        version_info = {
            "version_id": v.get('VersionId', '-'),
            "last_modified": v['LastModified'].isoformat(),
            "size": v.get('Size', 0),
            "storage_class": v.get('StorageClass', 'Standard'),
            "is_latest": v.get('IsLatest', False)
        }
        
        inventory[key]["versions"].append(version_info)
        inventory[key]["total_versions"] += 1
        inventory[key]["total_size"] += v.get('Size', 0)
        
        if v.get('IsLatest', False):
            inventory[key]["latest_version"] = version_info
    
    # Process delete markers
    for dm in delete_markers:
        key = dm['Key']
        delete_marker_info = {
            "version_id": dm.get('VersionId', '-'),
            "last_modified": dm['LastModified'].isoformat(),
            "size": 0,
            "storage_class": "DeleteMarker",
            "is_latest": dm.get('IsLatest', False)
        }
        
        inventory[key]["versions"].append(delete_marker_info)
        inventory[key]["total_versions"] += 1
        inventory[key]["has_delete_markers"] = True
        
        if dm.get('IsLatest', False):
            inventory[key]["latest_version"] = delete_marker_info

    # Convert defaultdict to regular dict and add metadata
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_objects": len(inventory),
            "total_versions": sum(item["total_versions"] for item in inventory.values()),
            "total_size": sum(item["total_size"] for item in inventory.values())
        },
        "objects": inventory
    }
    
    # Write to JSON file
    with open(json_file, 'w') as f:
        json.dump(output, f, indent=2, sort_keys=True)

def main():
    parser = argparse.ArgumentParser(description='Generate S3 bucket inventory')
    parser.add_argument('bucket', help='Name of the S3 bucket')
    parser.add_argument('path', nargs='?', default='', help='Path prefix in the bucket to inventory (optional)')
    parser.add_argument('--profile', help='AWS profile name')
    parser.add_argument('--output-dir', default='outputs', help='Output directory for inventory files')
    args = parser.parse_args()

    try:
        # Create output directory
        create_output_directory(args.output_dir)
        
        # Setup AWS client
        s3_client = setup_aws_client(args.profile)
        
        # Check bucket access
        check_bucket_access(s3_client, args.bucket)
        
        # Generate timestamp for filenames
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Define output files
        path_suffix = args.path.replace('/', '_').rstrip('_') if args.path else 'full'
        inventory_file = os.path.join(args.output_dir, f's3_inventory_{path_suffix}_{timestamp}.csv')
        summary_file = os.path.join(args.output_dir, f's3_inventory_summary_{path_suffix}_{timestamp}.txt')
        error_log = os.path.join(args.output_dir, f's3_inventory_errors_{timestamp}.log')
        json_file = os.path.join(args.output_dir, 'inventory.json')
        
        print(f"Starting inventory of bucket: {args.bucket}")
        if args.path:
            print(f"Inventorying path: {args.path}")
        
        # Get bucket inventory
        versions, delete_markers = get_bucket_inventory(s3_client, args.bucket, args.path)
        
        if not versions and not delete_markers:
            print(f"No objects found in path: {args.path}")
            return 0
        
        # Write inventory to CSV
        write_inventory_csv(versions, delete_markers, inventory_file)
        
        # Generate summary
        generate_summary(versions, delete_markers, args.bucket, summary_file)
        
        # Generate JSON inventory
        generate_json_inventory(versions, delete_markers, json_file)
        
        print("\nInventory complete!")
        print(f"Main inventory file: {inventory_file}")
        print(f"Summary file: {summary_file}")
        print(f"JSON inventory: {json_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        with open(error_log, 'w') as f:
            f.write(f"Error occurred at {datetime.now().isoformat()}\n")
            f.write(str(e))
        print(f"Error details written to: {error_log}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())
