output "lambda_function_name" {
    value = aws_lambda_function.api.function_name
}

output "lambda_arn" {
    value = aws_lambda_function.api.arn
}

output "api_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}