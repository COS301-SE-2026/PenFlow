variable "project_name" {
  description = "Name of project"
  type        = string
  default     = "penflow"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region in which PenFlow will be deployed."
  type        = string
  default     = "af-south-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the PenFlow VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones used by the deployment."
  type        = list(string)
  default = [
    "af-south-1a",
    "af-south-1b"
  ]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets."
  type        = list(string)
  default = [
    "10.0.1.0/24",
    "10.0.2.0/24"
  ]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets."
  type        = list(string)
  default = [
    "10.0.11.0/24",
    "10.0.12.0/24"
  ]
}

variable "db_name" {
  description = "PenFlow PostgreSQL database name."
  type        = string
  default     = "penflow"
}

variable "db_username" {
  description = "Master username for PostgreSQL."
  type        = string
  default     = "penflow_admin"
}

variable "db_password" {
  description = "Master password for PostgreSQL."
  type        = string
  sensitive   = true
}

variable "keycloak_db_name" {
  description = "Database used by Keycloak."
  type        = string
  default     = "keycloak"
}

variable "domain_name" {
  description = "Public domain for PenFlow"
  type        = string
  default     = "pen-flow.com"
}

variable "auth_domain_name" {
  description = "Public Keycloak hostname."
  type        = string
  default     = "auth.pen-flow.com"
}

variable "backend_desired_count" {
  description = "Desired backend ECS task count."
  type        = number
  default     = 0
}

variable "frontend_desired_count" {
  description = "Desired frontend ECS task count."
  type        = number
  default     = 0
}

variable "worker_desired_count" {
  description = "Desired worker ECS task count."
  type        = number
  default     = 0
}

variable "keycloak_desired_count" {
  description = "Desired keycloak ECS task count."
  type        = number
  default     = 0
}

variable "rabbitmq_username" {
  description = "Admin username for the RabbitMQ broker."
  type        = string
  default     = "penflow"
}

variable "rabbitmq_password" {
  description = "Password for the RabbitMQ broker."
  type        = string
  sensitive   = true
}

variable "rabbitmq_engine_version" {
  description = "Amazon MQ RabbitMQ engine version."
  type        = string
}

variable "backend_image_tag" {
  description = "Backend container image tag."
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Frontend container image tag."
  type        = string
  default     = "latest"
}

variable "worker_image_tag" {
  description = "Worker container image tag."
  type        = string
  default     = "latest"
}

variable "keycloak_image_tag" {
  description = "Keycloak container image tag."
  type        = string
  default     = "latest"
}

variable "access_token_lifespan_seconds" {
  description = "Fallback access token lifespan used only when access_token_expires_at is unavailable."
  type        = number
  default     = 900
}

variable "keycloak_bootstrap_admin_username" {
  type    = string
  default = "admin"
}

variable "keycloak_db_username" {
  description = "PostgreSQL user used by Keycloak."
  type        = string
  default     = "keycloak_app"
}

variable "app_env" {
  description = "Application environment."
  type        = string
  default     = "production"
}

variable "log_level" {
  description = "Application log level."
  type        = string
  default     = "INFO"
}

variable "smtp_host" {
  description = "SMTP server hostname."
  type        = string
  default     = ""
}

variable "smtp_port" {
  description = "SMTP server port."
  type        = number
  default     = 587
}

variable "smtp_user" {
  description = "SMTP username."
  type        = string
  default     = ""
}

variable "smtp_from" {
  description = "From address used by PenFlow."
  type        = string
  default     = ""
}

variable "db_backup_retention_period" {
  type        = number
  description = "Number of days to retain automated RDS backups."
  default     = 1
}

variable "email_worker_desired_count" {
  description = "Desired email-worker ECS task count."
  type        = number
  default     = 0
}

variable "schedule_worker_desired_count" {
  description = "Number of schedule worker ECS tasks"
  type        = number
  default     = 0
}

variable "celery_beat_desired_count" {
  description = "Number of Celery Beat ECS tasks; must be 0 or 1"
  type        = number
  default     = 0

  validation {
    condition     = contains([0, 1], var.celery_beat_desired_count)
    error_message = "celery_beat_desired_count must be either 0 or 1."
  }
}

variable "embedding_provider" {
  description = "Embedding provider used by the backend."
  type        = string
  default     = "bedrock"

  validation {
    condition = contains(
      ["bedrock", "openai_compatible"],
      var.embedding_provider
    )
    error_message = "embedding_provider must be bedrock or openai_compatible."
  }
}

variable "bedrock_region" {
  description = "AWS Region used for Amazon Bedrock inference."
  type        = string
  default     = "eu-west-1"
}

variable "bedrock_embedding_model_id" {
  description = "Amazon Bedrock embedding model identifier."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"

  validation {
    condition     = length(trimspace(var.bedrock_embedding_model_id)) > 0
    error_message = "bedrock_embedding_model_id cannot be empty."
  }
}

variable "bedrock_embedding_dimensions" {
  description = "Number of dimensions returned by the embedding model."
  type        = number
  default     = 1024

  validation {
    condition = contains(
      [256, 512, 1024],
      var.bedrock_embedding_dimensions
    )
    error_message = "Bedrock embedding dimensions must be 256, 512, or 1024."
  }
}

variable "generation_provider" {
  description = "Generation provider used by the RAG analyst."
  type        = string
  default     = "bedrock"
}

variable "bedrock_generation_region" {
  description = "AWS Region used for Bedrock answer generation."
  type        = string
  default     = "eu-west-1"
}

variable "bedrock_generation_model_id" {
  description = "Bedrock model or inference profile ID used for generation."
  type        = string

  validation {
    condition     = length(trimspace(var.bedrock_generation_model_id)) > 0
    error_message = "bedrock_generation_model_id cannot be empty."
  }
}

variable "bedrock_generation_resource_arns" {
  description = "Bedrock model and inference-profile ARNs generation may invoke."
  type        = list(string)

  validation {
    condition     = length(var.bedrock_generation_resource_arns) > 0
    error_message = "At least one Bedrock generation resource ARN is required."
  }
}

variable "bedrock_generation_max_tokens" {
  description = "Maximum answer tokens generated by the analyst."
  type        = number
  default     = 800

  validation {
    condition = (
      var.bedrock_generation_max_tokens >= 1
      && var.bedrock_generation_max_tokens <= 8192
    )
    error_message = "Generation max tokens must be between 1 and 8192."
  }
}

variable "bedrock_generation_temperature" {
  description = "Generation temperature for grounded security answers."
  type        = number
  default     = 0.1

  validation {
    condition = (
      var.bedrock_generation_temperature >= 0
      && var.bedrock_generation_temperature <= 1
    )
    error_message = "Generation temperature must be between 0 and 1."
  }
}