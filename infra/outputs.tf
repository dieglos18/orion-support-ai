output "sqs_queue_url" {
  description = "URL of the SQS queue for ticket ingestion"
  value       = aws_sqs_queue.ticket_queue.url
}

output "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.ticket_queue.arn
}

output "lambda_function_arn" {
  description = "ARN of the Lambda orchestrator function"
  value       = aws_lambda_function.orchestrator.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.orchestrator.function_name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for critical alerts"
  value       = aws_sns_topic.critical_alerts.arn
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule for critical tickets"
  value       = aws_cloudwatch_event_rule.critical_tickets.name
}
