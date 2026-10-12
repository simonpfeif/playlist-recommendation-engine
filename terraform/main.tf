terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
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

locals {
  ssm_prefix = "/playlist-recommendation-engine/spotify"
}

# Spotify credentials, read by the Lambda at runtime
resource "aws_ssm_parameter" "spotify_client_id" {
  name  = "${local.ssm_prefix}/client_id"
  type  = "SecureString"
  value = var.spotify_client_id
}

resource "aws_ssm_parameter" "spotify_client_secret" {
  name  = "${local.ssm_prefix}/client_secret"
  type  = "SecureString"
  value = var.spotify_client_secret
}

resource "aws_ssm_parameter" "spotify_refresh_token" {
  name  = "${local.ssm_prefix}/refresh_token"
  type  = "SecureString"
  value = var.spotify_refresh_token
}

# Let Lambda read the Spotify credentials
resource "aws_iam_role_policy" "lambda_ssm" {
  name = "read-spotify-credentials"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["ssm:GetParameters"]
        Effect   = "Allow"
        Resource = "arn:aws:ssm:${var.aws_region}:*:parameter${local.ssm_prefix}/*"
      }
    ]
  })
}

# Zip up the lambda code
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/../lambda/api/handler.py"
  output_path = "${path.module}/../lambda/api/handler.zip"
}

# The Lambda function itself
resource "aws_lambda_function" "api" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "playlist-recommendation-engine-api"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      SSM_PREFIX = local.ssm_prefix
    }
  }
}

# API Gateway
resource "aws_apigatewayv2_api" "gateway" {
  name          = "playlist-recommendation-engine-api"
  protocol_type = "HTTP"
}

# Connect API Gateway to Lambda
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.gateway.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

# Route GET requests to the Lambda
resource "aws_apigatewayv2_route" "get" {
  api_id    = aws_apigatewayv2_api.gateway.id
  route_key = "GET /"
  # Not public: callers must sign requests with AWS credentials
  authorization_type = "AWS_IAM"
  target             = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Deploy the API
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.gateway.id
  name        = "$default"
  auto_deploy = true
}

# Give API Gateway permission to invoke the Lambda
resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.gateway.execution_arn}/*/*"
}

# DynamoDB table for processed listening data
resource "aws_dynamodb_table" "listening_data" {
  name         = "playlist-recommendation-engine-listening-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }
}
