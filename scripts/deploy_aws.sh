#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Set OPENAI_API_KEY first." >&2
  exit 1
fi

REGION="${AWS_REGION:-ap-south-1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TF_DIR="${ROOT}/infra/terraform"

pushd "$TF_DIR" >/dev/null

terraform init

terraform apply   -target=aws_ecr_repository.app   -target=aws_secretsmanager_secret.openai   -target=random_id.suffix   -var="aws_region=${REGION}"   -auto-approve

ECR="$(terraform output -raw ecr_repository_url)"
SECRET_ARN="$(terraform output -raw openai_secret_arn)"

aws secretsmanager put-secret-value   --secret-id "$SECRET_ARN"   --secret-string "$OPENAI_API_KEY"   --region "$REGION" >/dev/null

REGISTRY="${ECR%%/*}"
aws ecr get-login-password --region "$REGION"   | docker login --username AWS --password-stdin "$REGISTRY"

docker build -t ai-compliance-auditor "$ROOT"
docker tag ai-compliance-auditor:latest "${ECR}:latest"
docker push "${ECR}:latest"

terraform apply   -var="aws_region=${REGION}"   -var="image_uri=${ECR}:latest"   -auto-approve

echo
echo "Application URL:"
terraform output -raw application_url
echo

popd >/dev/null
