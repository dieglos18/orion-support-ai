variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "orion-orchestrator"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "sqs_visibility_timeout" {
  description = "SQS message visibility timeout in seconds"
  type        = number
  default     = 70  # Must be > lambda_timeout
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock foundation model ID"
  type        = string
  default     = "amazon.nova-micro-v1:0"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "Orion AI Support Orchestrator"
    ManagedBy   = "Terraform"
    CostCenter  = "Engineering"
  }
}