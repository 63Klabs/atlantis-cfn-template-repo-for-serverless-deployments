#!/bin/bash

# Make script executable
# chmod +x upload_scripts.sh

# Basic usage
# ./upload_scripts.sh my-bucket atlantis/utilities

# Specify different source directory
# ./upload_scripts.sh my-bucket atlantis/utilities path/to/scripts

# With AWS profile
# AWS_PROFILE=myprofile ./upload_scripts.sh my-bucket atlantis/utilities



set -e  # Exit on error

# Configuration
BUCKET_NAME=${1:-""}
BASE_PATH=${2:-""}
SOURCE_DIR=${3:-"scripts"}
ZIP_NAME="template_scripts.zip"

# Function to show usage
usage() {
    echo "Usage: $0 <bucket-name> <base-path> [source-dir]"
    echo "Example: $0 my-bucket atlantis/utilities scripts"
    exit 1
}

# Check required parameters
if [ -z "$BUCKET_NAME" ] || [ -z "$BASE_PATH" ]; then
    usage
fi

# Function to clean up temporary files
cleanup() {
    rm -f "$ZIP_NAME" 2>/dev/null || true
}

# Set up error handling
trap cleanup EXIT

echo "Creating zip file from $SOURCE_DIR..."

# Create zip with deterministic content
find "$SOURCE_DIR" \( -name "*.sh" -o -name "*.md" -o -name "*.py" -o -name "requirements.txt" \) -type f | sort | zip "$ZIP_NAME" -@

if [ $? -ne 0 ]; then
    echo "Error creating zip file"
    exit 1
fi

# Calculate local MD5
LOCAL_MD5=$(md5sum "$ZIP_NAME" | cut -d' ' -f1)
LOCAL_ETAG=\"$LOCAL_MD5\"  # Add quotes to match S3's ETag format

echo "Local file hash: $LOCAL_ETAG"

# Get remote ETag if file exists
echo "Checking if file exists in S3..."
REMOTE_ETAG=$(aws s3api head-object \
    --bucket "$BUCKET_NAME" \
    --key "$BASE_PATH/$ZIP_NAME" \
    --query 'ETag' \
    --output text 2>/dev/null || echo "none")

echo "Remote file hash: $REMOTE_ETAG"

# Compare ETags and upload if different
if [ "$LOCAL_ETAG" != "$REMOTE_ETAG" ]; then
    echo "File has changed, uploading to S3..."
    aws s3 cp "$ZIP_NAME" "s3://$BUCKET_NAME/$BASE_PATH/$ZIP_NAME"
    if [ $? -eq 0 ]; then
        echo "Upload successful"
    else
        echo "Upload failed"
        exit 1
    fi
else
    echo "File unchanged, skipping upload"
fi

echo "Done!"
