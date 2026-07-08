variable "aws_region" {
  type        = string
  description = "AWS Region"
  default     = "ap-south-1"
}

variable "project_name" {
  type        = string
  description = "Resource prefix"
  default     = "ai-compliance-auditor"
}

variable "image_uri" {
  type        = string
  description = "Full ECR image URI including tag"
  default     = "public.ecr.aws/docker/library/python:3.12-slim"
}

variable "openai_model" {
  type    = string
  default = "gpt-4.1-mini"
}
