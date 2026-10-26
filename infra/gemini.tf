variable "gemini_generation_model" {
  type    = string
  default = "gemini-2.5-flash"
}

variable "gemini_max_output_tokens" {
  type    = number
  default = 2048

  validation {
    condition = (
      floor(var.gemini_max_output_tokens) == var.gemini_max_output_tokens &&
      var.gemini_max_output_tokens >= 1 &&
      var.gemini_max_output_tokens <= 8192
    )
    error_message = "Gemini output tokens must be an integer from 1 to 8192."
  }
}

variable "gemini_thinking_budget" {
  type    = number
  default = 0

  validation {
    condition = (
      floor(var.gemini_thinking_budget) == var.gemini_thinking_budget &&
      var.gemini_thinking_budget >= 0 &&
      var.gemini_thinking_budget <= 4096
    )
    error_message = "Gemini thinking budget must be an integer from 0 to 4096."
  }
}

variable "gemini_thinking_level" {
  type    = string
  default = "low"

  validation {
    condition     = contains(["minimal", "low", "medium", "high"], var.gemini_thinking_level)
    error_message = "Invalid Gemini thinking level."
  }
}

variable "gemini_embedding_dimensions" {
  type    = number
  default = 768

  validation {
    condition     = contains([768, 1536, 3072], var.gemini_embedding_dimensions)
    error_message = "Gemini embedding dimensions must be 768, 1536 or 3072."
  }
}

variable "gemini_timeout_seconds" {
  type    = number
  default = 60

  validation {
    condition = (
      floor(var.gemini_timeout_seconds) == var.gemini_timeout_seconds &&
      var.gemini_timeout_seconds >= 1 &&
      var.gemini_timeout_seconds <= 120
    )
    error_message = "Gemini timeout must be an integer from 1 to 120."
  }
}

locals {
  gemini_enabled = var.generation_provider == "gemini" || var.embedding_provider == "gemini"

  gemini_environment = local.gemini_enabled ? [
    {
      name  = "GEMINI_GENERATION_MODEL"
      value = var.gemini_generation_model
    },
    {
      name  = "GEMINI_MAX_OUTPUT_TOKENS"
      value = tostring(var.gemini_max_output_tokens)
    },
    {
      name  = "GEMINI_THINKING_BUDGET"
      value = tostring(var.gemini_thinking_budget)
    },
    {
      name  = "GEMINI_THINKING_LEVEL"
      value = var.gemini_thinking_level
    },
    {
      name  = "GEMINI_EMBEDDING_DIMENSIONS"
      value = tostring(var.gemini_embedding_dimensions)
    },
    {
      name  = "GEMINI_TIMEOUT_SECONDS"
      value = tostring(var.gemini_timeout_seconds)
    }
  ] : []

  gemini_secrets = local.gemini_enabled ? [
    {
      name      = "GEMINI_API_KEY"
      valueFrom = aws_secretsmanager_secret.gemini_api_key[0].arn
    }
  ] : []
}

resource "aws_secretsmanager_secret" "gemini_api_key" {
  count = local.gemini_enabled ? 1 : 0
  name  = "${local.name_prefix}/external-apis/gemini"
}