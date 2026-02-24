#!/usr/bin/env bash
# AI-Medicine: Deploy to AWS (ECR + EC2 with Docker)
# Uses credentials from aws_credentials file in this directory
#
# Usage:
#   ./deploy-aws.sh           # Full deploy (build + push + EC2) - needs local Docker
#   ./deploy-aws.sh --skip-build   # EC2 only - image must be in ECR (e.g. from GitHub Actions)

set -e

SKIP_BUILD=false
[[ "$1" == "--skip-build" ]] && SKIP_BUILD=true

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Fix Docker Desktop 500 error (API version mismatch) - use older API
export DOCKER_API_VERSION=1.41

CREDS_FILE="$SCRIPT_DIR/aws_credentials"
if [[ ! -f "$CREDS_FILE" ]]; then
  echo "ERROR: aws_credentials file not found at $CREDS_FILE"
  echo "Create it with format:"
  echo "  aws_access_key_id = YOUR_ACCESS_KEY"
  echo "  aws_secret_access_key = YOUR_SECRET_KEY"
  echo "  region = us-east-1"
  exit 1
fi

# Use custom credentials file
export AWS_SHARED_CREDENTIALS_FILE="$CREDS_FILE"

# Get region from credentials (default us-east-1)
AWS_REGION=$(grep -E '^\s*region\s*=' "$CREDS_FILE" 2>/dev/null | head -1 | sed 's/.*=\s*//' | tr -d ' ')
AWS_REGION=${AWS_REGION:-us-east-1}
export AWS_DEFAULT_REGION="$AWS_REGION"

echo "=== AI-Medicine AWS Deployment ==="
echo "Credentials: $CREDS_FILE"
echo "Region: $AWS_REGION"
echo ""

# Get AWS account ID
if ! AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region "$AWS_REGION" --query Account --output text 2>&1); then
  echo "ERROR: Failed to get AWS account."
  echo "AWS CLI output: $AWS_ACCOUNT_ID"
  echo ""
  echo "Troubleshooting:"
  echo "  1. Verify credentials in aws_credentials are correct (no extra spaces)"
  echo "  2. If you rotated keys, update aws_credentials with new keys"
  echo "  3. Test: AWS_SHARED_CREDENTIALS_FILE=$CREDS_FILE aws sts get-caller-identity"
  exit 1
fi
echo "Account ID: $AWS_ACCOUNT_ID"

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
IMAGE_URI="$ECR_URI/ai-medicine:latest"

# 1. Create ECR repository if not exists
echo ""
echo "--- Step 1: ECR Repository ---"
aws ecr describe-repositories --repository-names ai-medicine --region "$AWS_REGION" 2>/dev/null || \
  aws ecr create-repository --repository-name ai-medicine --region "$AWS_REGION"
echo "ECR repo ready."

# 2-4. Build and push (skip if --skip-build and image exists in ECR)
if [[ "$SKIP_BUILD" == true ]]; then
  echo ""
  echo "--- Skipping Docker build/push (--skip-build) ---"
  if ! aws ecr describe-images --repository-name ai-medicine --image-ids imageTag=latest --region "$AWS_REGION" 2>/dev/null; then
    echo "ERROR: Image ai-medicine:latest not found in ECR."
    echo "Run GitHub Actions workflow first, or run without --skip-build (needs working Docker)."
    exit 1
  fi
  echo "Image ai-medicine:latest found in ECR."
else
  echo ""
  echo "--- Step 2: Docker login to ECR ---"
  aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_URI"

  echo ""
  echo "--- Step 3: Build Docker image ---"
  docker build -t ai-medicine:latest .

  echo ""
  echo "--- Step 4: Push to ECR ---"
  docker tag ai-medicine:latest "$IMAGE_URI"
  docker push "$IMAGE_URI"
  echo "Image pushed: $IMAGE_URI"
fi

# 5. Create/update EC2 launch template and run instance
echo ""
echo "--- Step 5: EC2 Instance ---"

# Check for existing key pair
KEY_NAME="ai-medicine-key"
if ! aws ec2 describe-key-pairs --key-names "$KEY_NAME" --region "$AWS_REGION" 2>/dev/null; then
  echo "Creating key pair $KEY_NAME..."
  aws ec2 create-key-pair --key-name "$KEY_NAME" --region "$AWS_REGION" --query 'KeyMaterial' --output text > "$SCRIPT_DIR/${KEY_NAME}.pem"
  chmod 400 "$SCRIPT_DIR/${KEY_NAME}.pem"
  echo "Key saved to ${KEY_NAME}.pem - KEEP THIS SAFE"
fi

# Get default VPC and subnet
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=is-default,Values=true" --query "Vpcs[0].VpcId" --output text --region "$AWS_REGION")
SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query "Subnets[0].SubnetId" --output text --region "$AWS_REGION")

# Create security group if not exists
SG_NAME="ai-medicine-sg"
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" --query "SecurityGroups[0].GroupId" --output text --region "$AWS_REGION" 2>/dev/null || echo "None")
if [[ "$SG_ID" == "None" || -z "$SG_ID" ]]; then
  SG_ID=$(aws ec2 create-security-group --group-name "$SG_NAME" --description "AI-Medicine app" --vpc-id "$VPC_ID" --region "$AWS_REGION" --query 'GroupId' --output text)
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr 0.0.0.0/0 --region "$AWS_REGION"
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region "$AWS_REGION"
  aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 80 --cidr 0.0.0.0/0 --region "$AWS_REGION"
  echo "Security group created: $SG_ID"
fi

# Create IAM role for EC2 to pull from ECR (if not exists)
ROLE_NAME="ai-medicine-ec2-role"
PROFILE_NAME="ai-medicine-ec2-profile"
if ! aws iam get-role --role-name "$ROLE_NAME" 2>/dev/null; then
  echo "Creating IAM role for EC2..."
  aws iam create-role --role-name "$ROLE_NAME" --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
  aws iam attach-role-policy --role-name "$ROLE_NAME" --policy-arn "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  aws iam create-instance-profile --instance-profile-name "$PROFILE_NAME" 2>/dev/null || true
  aws iam add-role-to-instance-profile --instance-profile-name "$PROFILE_NAME" --role-name "$ROLE_NAME" 2>/dev/null || true
  echo "Waiting 15s for IAM profile to propagate..."
  sleep 15
fi

# User data: install Docker, AWS CLI, pull and run container
USER_DATA="#!/bin/bash
yum update -y
yum install -y docker aws-cli
systemctl start docker
systemctl enable docker
usermod -aG docker ec2-user
sleep 45
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI
docker pull $IMAGE_URI
docker run -d -p 8000:8000 --restart unless-stopped --name ai-medicine $IMAGE_URI
"

echo ""
echo "Launching EC2 instance (Amazon Linux 2023)..."
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $(aws ec2 describe-images --owners amazon --filters "Name=name,Values=al2023-ami-*-x86_64" "Name=state,Values=available" --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text --region "$AWS_REGION") \
  --instance-type t3.small \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SG_ID" \
  --subnet-id "$SUBNET_ID" \
  --iam-instance-profile Name="$PROFILE_NAME" \
  --user-data "$USER_DATA" \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=ai-medicine}]' \
  --region "$AWS_REGION" \
  --query 'Instances[0].InstanceId' --output text)

echo "Instance ID: $INSTANCE_ID"
echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$AWS_REGION"

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region "$AWS_REGION")
echo ""
echo "=== Instance Public IP: $PUBLIC_IP ==="
echo ""
echo "Waiting 60s for Docker to install..."
sleep 60

# Create run script and execute via SSM or SSH
# SSM might not be available on new instances - we'll use a simple approach
# Store the run commands for the user to execute
RUN_SCRIPT="$SCRIPT_DIR/ec2-run-instructions.sh"
cat > "$RUN_SCRIPT" << RUNEOF
#!/bin/bash
# Run these commands on EC2 (ssh ec2-user@$PUBLIC_IP) after the instance is ready:

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | sudo docker login --username AWS --password-stdin $ECR_URI

# Pull and run
sudo docker pull $IMAGE_URI
sudo docker run -d -p 8000:8000 --restart unless-stopped --name ai-medicine $IMAGE_URI

# App will be at: http://$PUBLIC_IP:8000
RUNEOF
chmod +x "$RUN_SCRIPT"

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo ""
echo "EC2 instance is running at: $PUBLIC_IP"
echo ""
echo "To finish setup, SSH in and run the container:"
echo "  ssh -i ${KEY_NAME}.pem ec2-user@$PUBLIC_IP"
echo ""
echo "Then on the EC2 instance:"
echo "  aws ecr get-login-password --region $AWS_REGION | sudo docker login --username AWS --password-stdin $ECR_URI"
echo "  sudo docker pull $IMAGE_URI"
echo "  sudo docker run -d -p 8000:8000 --restart unless-stopped --name ai-medicine $IMAGE_URI"
echo ""
echo "App URL: http://$PUBLIC_IP:8000"
echo ""
