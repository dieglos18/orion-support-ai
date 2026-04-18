terraform {
  required_version = ">= 1.7.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = var.tags
  }
}

# ========================================
# SQS Queue (Entry point for tickets)
# ========================================

resource "aws_sqs_queue" "ticket_queue" {
  name                       = "${var.project_name}-${var.environment}-tickets"
  visibility_timeout_seconds = var.sqs_visibility_timeout
  message_retention_seconds  = 1209600  # 14 days
  receive_wait_time_seconds  = 20       # Long polling
  
  # Dead Letter Queue configuration
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ticket_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "ticket_dlq" {
  name                      = "${var.project_name}-${var.environment}-tickets-dlq"
  message_retention_seconds = 1209600
}

# ========================================
# IAM Role for Lambda
# ========================================
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-${var.environment}-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

# Basic Lambda execution (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for SQS access (Least Privilege)
resource "aws_iam_role_policy" "lambda_sqs" {
  name = "sqs-access"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ]
      Resource = aws_sqs_queue.ticket_queue.arn
    }]
  })
}

# Policy for Bedrock access
resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "bedrock-access"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "bedrock:InvokeModel"
      ]
      Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_model_id}"
    }]
  })
}

# Policy for EventBridge (will use in Phase 4)
resource "aws_iam_role_policy" "lambda_eventbridge" {
  name = "eventbridge-access"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "events:PutEvents"
      ]
      Resource = "arn:aws:events:${var.aws_region}:*:event-bus/default"
    }]
  })
}

# ========================================
# Lambda layer (Python 3.12 deps — build before apply)
# ========================================
# Run from repo root: ./scripts/build_lambda_layer.sh
# Produces lambda_layer.zip with python/lib/python3.12/site-packages/...

resource "aws_lambda_layer_version" "python_deps" {
  filename            = "${path.module}/lambda_layer.zip"
  layer_name          = "${var.project_name}-${var.environment}-python-deps"
  compatible_runtimes = ["python3.12"]
  description         = "LangGraph, Pydantic, transitive deps (see requirements-lambda.txt)"

  source_code_hash = filebase64sha256("${path.module}/lambda_layer.zip")
}

# ========================================
# Lambda Function (application code only)
# ========================================

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_lambda_function" "orchestrator" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-${var.environment}-orchestrator"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_handler.handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory

  layers = [aws_lambda_layer_version.python_deps.arn]

  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      ENVIRONMENT      = var.environment
      LOG_LEVEL        = "INFO"
    }
  }
}

# ========================================
# SQS -> Lambda Event Source Mapping
# ========================================

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.ticket_queue.arn
  function_name    = aws_lambda_function.orchestrator.arn
  batch_size       = 1
  enabled          = true
}

# ========================================
# EventBridge Rule (Critical Alerts)
# ========================================

resource "aws_cloudwatch_event_rule" "critical_tickets" {
  name        = "${var.project_name}-${var.environment}-critical-tickets"
  description = "Triggers on critical urgency tickets (level 4-5)"
  
  event_pattern = jsonencode({
    source      = ["custom.support"]
    detail-type = ["Critical Ticket Alert"]
    detail = {
      urgency = [4, 5]
    }
  })
}

# EventBridge target (SNS topic - Phase 4)
resource "aws_sns_topic" "critical_alerts" {
  name = "${var.project_name}-${var.environment}-critical-alerts"
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.critical_tickets.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.critical_alerts.arn
}

resource "aws_sns_topic_policy" "eventbridge_publish" {
  arn = aws_sns_topic.critical_alerts.arn
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "events.amazonaws.com"
      }
      Action   = "SNS:Publish"
      Resource = aws_sns_topic.critical_alerts.arn
    }]
  })
}