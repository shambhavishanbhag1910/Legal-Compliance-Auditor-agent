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

variable "groq_model" {
  type        = string
  description = "Groq model name"
  default     = "openai/gpt-oss-20b"
}


variable "groq_base_url" {
  type        = string
  description = "Groq OpenAI-compatible base URL"
  default     = "https://api.groq.com/openai/v1"
}
