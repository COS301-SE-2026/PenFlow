output "vpc_id" {
  description = "ID of the PenFlow VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs used by load balancers and ECS."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs used by databases."
  value       = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  value = aws_security_group.alb.id
}

output "frontend_security_group_id" {
  value = aws_security_group.frontend.id
}

output "backend_security_group_id" {
  value = aws_security_group.backend.id
}

output "worker_security_group_id" {
  value = aws_security_group.worker.id
}

output "keycloak_security_group_id" {
  value = aws_security_group.keycloak.id
}

output "rds_security_group_id" {
  value = aws_security_group.rds.id
}

output "backend_ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "frontend_ecr_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "worker_ecr_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "keycloak_ecr_repository_url" {
  value = aws_ecr_repository.keycloak.repository_url
}

output "ecs_execution_role_arn" {
  value = aws_iam_role.ecs_execution.arn
}

output "backend_task_role_arn" {
  value = aws_iam_role.backend_task.arn
}

output "frontend_task_role_arn" {
  value = aws_iam_role.frontend_task.arn
}

output "worker_task_role_arn" {
  value = aws_iam_role.worker_task.arn
}

output "keycloak_task_role_arn" {
  value = aws_iam_role.keycloak_task.arn
}

output "rds_endpoint" {
  description = "PostgreSQL RDS endpoint."
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "PostgreSQL RDS port."
  value       = aws_db_instance.main.port
}

output "rds_database_name" {
  description = "Primary PenFlow database name."
  value       = aws_db_instance.main.db_name
}

output "alb_dns_name" {
  description = "DNS name of the application load balancer."
  value       = aws_lb.main.dns_name
}

output "frontend_target_group_arn" {
  value = aws_lb_target_group.frontend.arn
}

output "backend_target_group_arn" {
  value = aws_lb_target_group.backend.arn
}

output "keycloak_target_group_arn" {
  value = aws_lb_target_group.keycloak.arn
}

output "rabbitmq_broker_id" {
  value = aws_mq_broker.rabbitmq.id
}

output "rabbitmq_endpoints" {
  value     = aws_mq_broker.rabbitmq.instances[*].endpoints
  sensitive = true
}

output "rabbitmq_security_group_id" {
  value = aws_security_group.rabbitmq.id
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "db_bootstrap_task_definition_arn" {
  value = aws_ecs_task_definition.db_bootstrap.arn
}

output "db_bootstrap_security_group_id" {
  value = aws_security_group.backend.id
}

output "acm_certificate_arn" {
  value = aws_acm_certificate.main.arn
}

output "acm_validation_records" {
  value = {
    for option in aws_acm_certificate.main.domain_validation_options :
    option.domain_name => {
      name  = option.resource_record_name
      type  = option.resource_record_type
      value = option.resource_record_value
    }
  }
}

output "application_domain" {
  value = var.domain_name
}

output "authentication_domain" {
  value = var.auth_domain_name
}

output "db_bootstrap_ecr_repository_url" {
  value = aws_ecr_repository.db_bootstrap.repository_url
}

output "email_worker_security_group_id" {
  value = aws_security_group.email_worker.id
}

output "email_worker_task_role_arn" {
  value = aws_iam_role.email_worker_task.arn
}

output "email_worker_service_name" {
  value = aws_ecs_service.email_worker.name
}