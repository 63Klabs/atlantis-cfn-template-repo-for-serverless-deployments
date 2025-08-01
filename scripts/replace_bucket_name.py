#!/usr/bin/env python3
import os
import sys

def replace_placeholder(directory, bucket_name):
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 's3://S3_TEMPLATE_BUCKET' in content:
                    content = content.replace('s3://S3_TEMPLATE_BUCKET', f's3://{bucket_name}')
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Updated: {file_path}")
            except (UnicodeDecodeError, PermissionError):
                continue

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python replace_bucket_name.py <template_directory> <bucket_name>")
        sys.exit(1)
    
    template_dir = sys.argv[1]
    bucket_name = sys.argv[2]
    
    if not os.path.exists(template_dir):
        print(f"Error: Directory {template_dir} does not exist")
        sys.exit(1)
    
    replace_placeholder(template_dir, bucket_name)
