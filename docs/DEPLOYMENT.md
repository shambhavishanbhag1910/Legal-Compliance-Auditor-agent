# AWS Deployment

## Runtime Architecture

The application is deployed using:

- Docker
- Amazon ECR
- Amazon ECS Fargate
- Application Load Balancer
- Amazon S3
- AWS Secrets Manager
- Amazon CloudWatch Logs
- Terraform

## Deployment Flow

1. Build Docker image locally
2. Push image to Amazon ECR
3. Store Groq API key in AWS Secrets Manager
4. Provision infrastructure with Terraform
5. Run FastAPI + frontend on ECS Fargate
6. Route public traffic through Application Load Balancer

## Terraform Commands

Validate:

```powershell
terraform -chdir=infra/terraform validate