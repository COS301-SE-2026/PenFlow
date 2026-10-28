variable "rate_limit_proxy_secret" {
  type      = string
  sensitive = true

  validation {
    condition = can(regex(
      "^[a-fA-F0-9]{64}$",
      var.rate_limit_proxy_secret
    ))
    error_message = "Use a 64-character random hexadecimal proxy secret."
  }
}

variable "rate_limit_redis_password" {
  type      = string
  sensitive = true

  validation {
    condition = can(regex(
      "^[a-fA-F0-9]{64}$",
      var.rate_limit_redis_password
    ))
    error_message = "Use a 64-character random hexadecimal Redis password."
  }
}

resource "aws_security_group" "rate_limit" {
  name   = "${local.name_prefix}-rate-limit"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }
}

resource "aws_elasticache_subnet_group" "rate_limit" {
  name       = "${local.name_prefix}-rate-limit"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_parameter_group" "rate_limit" {
  name   = "${local.name_prefix}-rate-limit"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "noeviction"
  }
}

resource "aws_elasticache_replication_group" "rate_limit" {
  replication_group_id = "${local.name_prefix}-rate-limit"
  description          = "Shared API rate-limit counters"

  engine         = "redis"
  engine_version = "7.1"
  node_type      = "cache.t4g.micro"
  port           = 6379

  parameter_group_name = aws_elasticache_parameter_group.rate_limit.name

  num_cache_clusters         = 1
  automatic_failover_enabled = false

  subnet_group_name  = aws_elasticache_subnet_group.rate_limit.name
  security_group_ids = [aws_security_group.rate_limit.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  transit_encryption_mode    = "required"

  auth_token               = var.rate_limit_redis_password
  snapshot_retention_limit = 0
}

resource "aws_secretsmanager_secret" "rate_limit_proxy_secret" {
  name = "${local.name_prefix}/rate-limit/proxy-secret"
}

resource "aws_secretsmanager_secret_version" "rate_limit_proxy_secret" {
  secret_id     = aws_secretsmanager_secret.rate_limit_proxy_secret.id
  secret_string = var.rate_limit_proxy_secret
}

resource "aws_secretsmanager_secret" "rate_limit_storage_uri" {
  name = "${local.name_prefix}/rate-limit/storage-uri"
}

resource "aws_secretsmanager_secret_version" "rate_limit_storage_uri" {
  secret_id = aws_secretsmanager_secret.rate_limit_storage_uri.id

  secret_string = format(
    "rediss://:%s@%s:6379/0",
    var.rate_limit_redis_password,
    aws_elasticache_replication_group.rate_limit.primary_endpoint_address
  )
}