output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}

output "groq_secret_arn" {
  value = aws_secretsmanager_secret.groq.arn
}

output "s3_bucket_name" {
  value = aws_s3_bucket.data.bucket
}

output "application_url" {
  value = "http://${aws_lb.app.dns_name}"
}
