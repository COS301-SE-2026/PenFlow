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

variable "email_from" {
  description = "Verified Amazon SES sender address."
  type        = string
}

variable "ses_identity_arn" {
  description = "Verified Amazon SES identity ARN permitted for sending."
  type        = string
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