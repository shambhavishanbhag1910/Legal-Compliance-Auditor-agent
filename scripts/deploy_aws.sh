#!/usr/bin/env bash

set -euo pipefail


REGION="${AWS_REGION:-ap-south-1}"


if [[ -z "${GROQ_API_KEY:-}" ]]; then
  echo "ERROR: GROQ_API_KEY is not set."
  echo "Set it before running this script:"
  echo 'export GROQ_API_KEY="your-key-here"'
  exit 1
fi


echo "Using AWS region: ${REGION}"


# ---------------------------------------------------------
# Move to Terraform directory
# ---------------------------------------------------------

cd "$(dirname "$0")/../infra/terraform"


# ---------------------------------------------------------
# Initialize Terraform
# ---------------------------------------------------------

echo "Initializing Terraform..."

terraform init


# ---------------------------------------------------------
# Create bootstrap resources first
# ---------------------------------------------------------

echo "Creating ECR repository and Groq secret..."

terraform apply \
  -target=aws_ecr_repository.app \
  -target=aws_secretsmanager_secret.groq \
  -target=random_id.suffix \
  -var="aws_region=${REGION}" \
  -auto-approve


# ---------------------------------------------------------
# Read Terraform outputs
# ---------------------------------------------------------

ECR_URL="$(terraform output -raw ecr_repository_url)"

SECRET_ARN="$(terraform output -raw groq_secret_arn)"


echo "ECR repository: ${ECR_URL}"


# ---------------------------------------------------------
# Store Groq API key in Secrets Manager
# ---------------------------------------------------------

echo "Updating Groq API key in AWS Secrets Manager..."

aws secretsmanager put-secret-value \
  --secret-id "${SECRET_ARN}" \
  --secret-string "${GROQ_API_KEY}" \
  --region "${REGION}" \
  >/dev/null


# ---------------------------------------------------------
# Authenticate Docker with ECR
# ---------------------------------------------------------

echo "Authenticating Docker with Amazon ECR..."

aws ecr get-login-password \
  --region "${REGION}" \
  | docker login \
      --username AWS \
      --password-stdin \
      "${ECR_URL%/*}"


# ---------------------------------------------------------
# Build Docker image
# ---------------------------------------------------------

echo "Building Docker image..."

docker build \
  -t ai-compliance-auditor:latest \
  ../..


# ---------------------------------------------------------
# Tag image
# ---------------------------------------------------------

echo "Tagging Docker image..."

docker tag \
  ai-compliance-auditor:latest \
  "${ECR_URL}:latest"


# ---------------------------------------------------------
# Push image to ECR
# ---------------------------------------------------------

echo "Pushing Docker image to ECR..."

docker push \
  "${ECR_URL}:latest"


# ---------------------------------------------------------
# Deploy full infrastructure
# ---------------------------------------------------------

echo "Deploying complete AWS infrastructure..."

terraform apply \
  -var="aws_region=${REGION}" \
  -var="image_tag=latest" \
  -auto-approve


echo ""
echo "Deployment complete."
echo ""

terraform output