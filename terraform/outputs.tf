output "lambda_function_name" {
  value = aws_lambda_function.api.function_name
}

output "lambda_arn" {
  value = aws_lambda_function.api.arn
}

output "api_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}
output "dynamodb_table_name" {
  value = aws_dynamodb_table.listening_data.name
}
