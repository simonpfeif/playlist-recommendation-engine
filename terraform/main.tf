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
  timeout = 30

  environment {
    variables = {
        SPOTIFY_CLIENT_ID = var.spotify_client_id
        SPOTIFY_CLIENT_SECRET = var.spotify_client_secret
        SPOTIFY_REFRESH_TOKEN = var.spotify_refresh_token
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
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
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
