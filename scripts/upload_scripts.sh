#!/bin/bash

# Make script executable
# chmod +x upload_scripts.sh

# Basic usage
# ./upload_scripts.sh my-bucket atlantis/utilities

# Specify different source directory
# ./upload_scripts.sh my-bucket atlantis/utilities path/to/scripts

# With AWS profile
# ./upload_scripts.sh my-bucket atlantis/utilities scripts --profile myprofile

# With dryrun
# ./upload_scripts.sh my-bucket atlantis/utilities --dryrun

set -e  # Exit on error

# Configuration
BUCKET_NAME=""
BASE_PATH=""
SOURCE_DIR="scripts"
ZIP_NAME="template_scripts.zip"
AWS_PROFILE=""
DRYRUN=""

# Function to show usage
usage() {
    echo "Usage: $0 <bucket-name> <base-path> [source-dir] [--profile profile-name] [--dryrun]"
    echo "Example: $0 my-bucket atlantis/utilities scripts --profile myprofile"
    echo ""
    echo "Options:"
    echo "  --profile   Specify AWS profile"
    echo "  --dryrun    Show what would be uploaded without actually uploading"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            AWS_PROFILE="$2"
            shift 2
            ;;
        --dryrun)
            DRYRUN="true"
            shift
            ;;
        *)
            if [ -z "$BUCKET_NAME" ]; then
                BUCKET_NAME="$1"
            elif [ -z "$BASE_PATH" ]; then
                BASE_PATH="$1"
            elif [ "$1" != "--profile" ]; then  # Only set SOURCE_DIR if not --profile
                SOURCE_DIR="$1"
            fi
            shift
            ;;
    esac
done

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

# Build AWS command with optional profile
AWS_CMD="aws"
if [ -n "$AWS_PROFILE" ]; then
    AWS_CMD="aws --profile $AWS_PROFILE"
    echo "Using AWS profile: $AWS_PROFILE"
else
    # Check if AWS credentials are available
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo "Error: No AWS credentials found. Please either:"
        echo "1. Configure default credentials using 'aws configure'"
        echo "2. Set AWS environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
        echo "3. Use --profile option to specify a profile"
        exit 1
    fi
    echo "Using default AWS credentials"
fi

# Get remote ETag if file exists
echo "Checking if file exists in S3..."
REMOTE_ETAG=$($AWS_CMD s3api head-object \
    --bucket "$BUCKET_NAME" \
    --key "$BASE_PATH/$ZIP_NAME" \
    --query 'ETag' \
    --output text 2>/dev/null || echo "none")

echo "Remote file hash: $REMOTE_ETAG"

# Compare ETags and upload if different
if [ "$LOCAL_ETAG" != "$REMOTE_ETAG" ]; then
    if [ -n "$DRYRUN" ]; then
        echo "[DRYRUN] Would upload $ZIP_NAME to s3://$BUCKET_NAME/$BASE_PATH/$ZIP_NAME"
        echo "[DRYRUN] File has changed - Local hash: $LOCAL_ETAG, Remote hash: $REMOTE_ETAG"
    else
        echo "File has changed, uploading to S3..."
        $AWS_CMD s3 cp "$ZIP_NAME" "s3://$BUCKET_NAME/$BASE_PATH/$ZIP_NAME"
        if [ $? -eq 0 ]; then
            echo "Upload successful"
        else
            echo "Upload failed"
            exit 1
        fi
    fi
else
    if [ -n "$DRYRUN" ]; then
        echo "[DRYRUN] Would skip upload - file unchanged"
        echo "[DRYRUN] Local hash matches remote: $LOCAL_ETAG"
    else
        echo "File unchanged, skipping upload"
    fi
fi

if [ -n "$DRYRUN" ]; then
    echo "Dryrun completed successfully"
else
    echo "Done!"
fi
