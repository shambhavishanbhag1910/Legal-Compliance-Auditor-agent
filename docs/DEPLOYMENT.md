# AWS Deployment

This document explains how to deploy AI Legal & Compliance Auditor to AWS using Docker, Amazon ECR, Amazon ECS Fargate, Application Load Balancer, Amazon S3, AWS Secrets Manager, CloudWatch Logs, and Terraform.

## Runtime Architecture

```text
User Browser
    |
    v
Application Load Balancer
    |
    v
ECS Fargate Task
    |
    v
FastAPI + Frontend
    |
    +--> Amazon S3
    |
    +--> Groq API
    |
    `--> CloudWatch Logs
```

## AWS Services Used

- Amazon ECR for Docker image storage
- Amazon ECS Fargate for container runtime
- Application Load Balancer for public HTTP routing
- Amazon S3 for document and audit persistence
- AWS Secrets Manager for `GROQ_API_KEY`
- Amazon CloudWatch Logs for runtime logs
- IAM roles and policies for ECS execution and S3 access
- EC2 security groups for ALB-to-task traffic
- Terraform for infrastructure provisioning

## Deployment Flow

1. Validate Terraform.
2. Bootstrap ECR and Secrets Manager resources.
3. Store the Groq API key in Secrets Manager.
4. Build the Docker image.
5. Push the Docker image to ECR.
6. Run Terraform plan using the real ECR image URI.
7. Apply Terraform to create ECS, ALB, S3, IAM, and CloudWatch resources.
8. Verify the public application URL.
9. Test `/health`.
10. Open the frontend.

## Prerequisites

Required locally:

- AWS CLI installed and authenticated
- Terraform installed
- Docker Desktop running
- Groq API key
- PowerShell on Windows, or Bash on macOS/Linux

Required AWS permissions:

- ECR repository create/read/write
- ECS cluster, task definition, and service permissions
- IAM role and policy permissions
- S3 bucket and object permissions
- Secrets Manager create/read/write permissions
- CloudWatch Logs permissions
- Elastic Load Balancing permissions
- EC2 VPC, subnet, and security group permissions

## Environment Variables

Default region:

```text
ap-south-1
```

Set the Groq API key locally before deployment:

```powershell
$env:GROQ_API_KEY="your-groq-key"
```

macOS/Linux:

```bash
export GROQ_API_KEY="your-groq-key"
```

Do not commit `.env`, API keys, Terraform state files, or AWS credentials.

## Validate Terraform

```powershell
terraform -chdir=infra/terraform validate
```

Expected result:

```text
Success! The configuration is valid.
```

## Bootstrap ECR and Secrets Manager

The image must exist in ECR before the full ECS service deployment can run.

```powershell
terraform -chdir=infra/terraform apply `
  -target="aws_ecr_repository.app" `
  -target="aws_secretsmanager_secret.groq" `
  -target="random_id.suffix" `
  -var="aws_region=ap-south-1" `
  -auto-approve
```

This creates:

- ECR repository
- Secrets Manager secret metadata
- random suffix used by resource names

## Store Groq API Key in Secrets Manager

```powershell
$SecretArn = terraform -chdir=infra/terraform output -raw groq_secret_arn

aws secretsmanager put-secret-value `
  --secret-id $SecretArn `
  --secret-string $env:GROQ_API_KEY `
  --region ap-south-1
```

## Build Docker Image

```powershell
docker build -t ai-compliance-auditor:latest .
```

## Login to Amazon ECR

```powershell
$EcrUrl = terraform -chdir=infra/terraform output -raw ecr_repository_url
$Registry = $EcrUrl.Split('/')[0]

aws ecr get-login-password --region ap-south-1 | `
  docker login --username AWS --password-stdin $Registry
```

## Tag and Push Docker Image

```powershell
docker tag ai-compliance-auditor:latest "${EcrUrl}:latest"
docker push "${EcrUrl}:latest"
```

## Confirm Image Exists in ECR

```powershell
aws ecr describe-images `
  --repository-name ai-compliance-auditor `
  --image-ids imageTag=latest `
  --region ap-south-1
```

## Plan Full Deployment

```powershell
terraform -chdir=infra/terraform plan `
  -var="aws_region=ap-south-1" `
  -var="image_uri=${EcrUrl}:latest"
```

Review the plan. It should include resources such as:

- ECS Fargate service
- ECS task definition
- Application Load Balancer
- Target group
- S3 bucket
- IAM roles and policies
- CloudWatch log group

## Apply Full Deployment

```powershell
terraform -chdir=infra/terraform apply `
  -var="aws_region=ap-south-1" `
  -var="image_uri=${EcrUrl}:latest"
```

Type:

```text
yes
```

Terraform will create or update the AWS infrastructure.

## Get Application URL

```powershell
$AppUrl = terraform -chdir=infra/terraform output -raw application_url
$AppUrl
```

Open the returned URL in a browser.

## Health Check

```powershell
Invoke-RestMethod "$AppUrl/health"
```

Expected response:

```json
{
  "status": "healthy",
  "storage_backend": "s3",
  "model_configured": true,
  "api_key_configured": true
}
```

## ECS Service Verification

```powershell
aws ecs describe-services `
  --cluster ai-compliance-auditor-cluster `
  --services ai-compliance-auditor-service `
  --region ap-south-1 `
  --query "services[0].{Status:status,Desired:desiredCount,Running:runningCount,Pending:pendingCount}"
```

Expected values:

```json
{
  "Status": "ACTIVE",
  "Desired": 1,
  "Running": 1,
  "Pending": 0
}
```

## ALB Target Health

```powershell
$TgArn = aws elbv2 describe-target-groups `
  --names ai-compliance-auditor-tg `
  --region ap-south-1 `
  --query "TargetGroups[0].TargetGroupArn" `
  --output text

aws elbv2 describe-target-health `
  --target-group-arn $TgArn `
  --region ap-south-1
```

Expected target state:

```text
healthy
```

## CloudWatch Logs

```powershell
aws logs tail /ecs/ai-compliance-auditor `
  --region ap-south-1 `
  --since 30m
```

Follow logs:

```powershell
aws logs tail /ecs/ai-compliance-auditor `
  --region ap-south-1 `
  --follow
```

## Runtime Configuration

The ECS task runs the application with:

```text
STORAGE_BACKEND=s3
S3_BUCKET=<terraform-created-bucket>
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_API_KEY=<injected from AWS Secrets Manager>
MAX_TOOL_STEPS=2
SELF_CONSISTENCY_RUNS=3
```

## Current Cloud Limitation

The current `/audits` endpoint is synchronous. For small documents and controlled demos, this is acceptable. For production-grade cloud execution, the audit workflow should become asynchronous:

```text
POST /audit-jobs
    |
    v
202 Accepted + job_id
    |
    v
Background audit execution
    |
    v
GET /audit-jobs/{job_id}
    |
    v
GET /audits/{audit_id}
```

This avoids browser and load-balancer timeout issues for larger documents and multi-step LLM calls.

## Destroy Infrastructure

AWS resources can create ongoing cost. Destroy when the demo is complete:

```powershell
$EcrUrl = terraform -chdir=infra/terraform output -raw ecr_repository_url

terraform -chdir=infra/terraform destroy `
  -var="aws_region=ap-south-1" `
  -var="image_uri=${EcrUrl}:latest"
```

S3 bucket deletion may fail if the bucket contains objects. Empty the bucket first if needed.

## Files Not to Commit

Do not commit:

```text
.env
terraform.tfstate
terraform.tfstate.backup
.terraform/
eval_results/
*.pem
*.key
```

## Deployment Status Summary

This deployment validates:

- containerized FastAPI + frontend runtime
- public ALB routing
- ECS Fargate service startup
- S3-backed storage configuration
- Secrets Manager injection of Groq API key
- CloudWatch log group configuration
- Terraform-managed infrastructure
