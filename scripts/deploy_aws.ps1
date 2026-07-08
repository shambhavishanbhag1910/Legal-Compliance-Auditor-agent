$ErrorActionPreference = "Stop"

if (-not $env:OPENAI_API_KEY) {
    throw "Set OPENAI_API_KEY in the current PowerShell session first."
}

$Region = if ($env:AWS_REGION) { $env:AWS_REGION } else { "ap-south-1" }
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$TfDir = Join-Path $Root "infra\terraform"

Push-Location $TfDir
try {
    terraform init

    terraform apply `
        -target=aws_ecr_repository.app `
        -target=aws_secretsmanager_secret.openai `
        -target=random_id.suffix `
        -var="aws_region=$Region" `
        -auto-approve

    $Ecr = terraform output -raw ecr_repository_url
    $SecretArn = terraform output -raw openai_secret_arn

    aws secretsmanager put-secret-value `
        --secret-id $SecretArn `
        --secret-string $env:OPENAI_API_KEY `
        --region $Region | Out-Null

    $Registry = $Ecr.Split("/")[0]
    aws ecr get-login-password --region $Region |
        docker login --username AWS --password-stdin $Registry

    docker build -t ai-compliance-auditor $Root
    docker tag ai-compliance-auditor:latest "${Ecr}:latest"
    docker push "${Ecr}:latest"

    terraform apply `
        -var="aws_region=$Region" `
        -var="image_uri=${Ecr}:latest" `
        -auto-approve

    Write-Host ""
    Write-Host "Application URL:"
    terraform output -raw application_url
    Write-Host ""
}
finally {
    Pop-Location
}
