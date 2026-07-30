resource "aws_ecs_task_definition" "db_bootstrap" {
  family                   = "${local.name_prefix}-db-bootstrap"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = 256
  memory = 512

  execution_role_arn = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name      = "db-bootstrap"
      image     = "${aws_ecr_repository.db_bootstrap.repository_url}:latest"
      essential = true

      environment = [
        { name = "PGHOST", value = aws_db_instance.main.address },
        { name = "PGPORT", value = tostring(aws_db_instance.main.port) },
        { name = "PGDATABASE", value = var.db_name },
        { name = "PGUSER", value = var.db_username },
        { name = "KEYCLOAK_DB_NAME", value = var.keycloak_db_name },
        { name = "KEYCLOAK_DB_USER", value = var.keycloak_db_username }
      ]

      secrets = [
        { name = "PGPASSWORD", valueFrom = aws_secretsmanager_secret.db_password.arn },
        { name = "KEYCLOAK_DB_PASSWORD", valueFrom = aws_secretsmanager_secret.keycloak_db_password.arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "db-bootstrap"
        }
      }
    }
  ])
}