terraform {
    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "~> 5.0"
        }
    }
}

provider "aws" {
    region = var.aws_region
}

# IAM role that Lambda assumes when it runs
resource "aws_iam_role" "lambda_role" {
  name = "playlist-recommendation-engine-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Attach basic Lambda permissions (CloudWatch logging)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
    role       = aws_iam_role.lambda_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Zip up the lambda code
data "archive_file" "lambda_zip" {
    type = "zip"
    source_file = "${path.module}/../lambda/api/handler.py"
    output_path = "${path.module}/../lambda/api/handler.zip"
}

# The Lambda function itself
resource "aws_lambda_function" "api" {
    filename = data.archive_file.lambda_zip.output_path
    function_name = "playlist-recommendation-engine-api"
    role = aws_iam_role.lambda_role.arn
    handler = "handler.lambda_handler"
    runtime = "python3.12"
    source_code_hash = data.archive_file.lambda_zip.output_base64sha256
}