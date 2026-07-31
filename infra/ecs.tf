resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  tags = {
    Name = "${local.name_prefix}-cluster"
  }
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name_prefix}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = 512
  memory = 1024

  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.backend_task.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "penflow-backend"
      image     = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
      essential = true

      cpu               = 512
      memory            = 1024
      memoryReservation = 768

      portMappings = [
        {
          containerPort = 3001
          hostPort      = 3001
          protocol      = "tcp"
          name          = "penflow-backend-3001-tcp"
          appProtocol   = "http"
        }
      ]

      environment = [
        { name = "APP_ENV", value = var.app_env },
        { name = "AUTH_PROVIDER", value = "keycloak" },
        { name = "LOG_LEVEL", value = var.log_level },
        { name = "SMTP_HOST", value = var.smtp_host },
        { name = "SMTP_PORT", value = tostring(var.smtp_port) },
        { name = "SMTP_USER", value = var.smtp_user },
        { name = "SMTP_FROM", value = var.smtp_from },
        { name = "REPORT_STORAGE", value = "s3" },
        { name = "REPORT_S3_BUCKET", value = aws_s3_bucket.reports.bucket },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "KEYCLOAK_AUDIENCE", value = "penflow-api" },
        { name = "KEYCLOAK_ISSUER", value = "https://${var.auth_domain_name}/realms/penflow" },
        { name = "DATABASE_HOST", value = aws_db_instance.main.address },
        { name = "DATABASE_PORT", value = tostring(aws_db_instance.main.port) },
        { name = "DATABASE_NAME", value = var.db_name },
        { name = "DATABASE_USER", value = var.db_username },
        { name = "RABBITMQ_PROTOCOL", value = "amqps" },
        {
          name  = "RABBITMQ_HOST",
          value = replace(replace(aws_mq_broker.rabbitmq.instances[0].endpoints[0], "amqps://", ""), ":5671", "")
        },
        { name = "RABBITMQ_PORT", value = "5671" },
        { name = "RABBITMQ_USERNAME", value = var.rabbitmq_username }
      ]

      secrets = [
        { name = "DATABASE_PASSWORD", valueFrom = aws_secretsmanager_secret.db_password.arn },
        { name = "RABBITMQ_PASSWORD", valueFrom = aws_secretsmanager_secret.rabbitmq_password.arn },
        { name = "HIBP_API_KEY", valueFrom = aws_secretsmanager_secret.hibp_api_key.arn },
        { name = "SHODAN_API_KEY", valueFrom = aws_secretsmanager_secret.shodan_api_key.arn },
        { name = "URLSCAN_API_KEY", valueFrom = aws_secretsmanager_secret.urlscan_api_key.arn },
        { name = "SMTP_PASSWORD", valueFrom = aws_secretsmanager_secret.smtp_password.arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.name_prefix}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = 256
  memory = 512

  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.frontend_task.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "penflow-frontend"
      image     = "${aws_ecr_repository.frontend.repository_url}:${var.frontend_image_tag}"
      essential = true

      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
          protocol      = "tcp"
          name          = "penflow-frontend-3000-tcp"
          appProtocol   = "http"
        }
      ]

      environment = [
        { name = "API_URL", value = "https://${var.domain_name}" },
        { name = "APP_URL", value = "https://${var.domain_name}" },
        { name = "KEYCLOAK_PUBLIC_URL", value = "https://${var.auth_domain_name}" },
        { name = "KEYCLOAK_INTERNAL_URL", value = "https://${var.auth_domain_name}" },
        { name = "KEYCLOAK_REALM", value = "penflow" },
        { name = "KEYCLOAK_CLIENT_ID", value = "penflow-web" },
        { name = "NEXT_PUBLIC_ACCESS_TOKEN_LIFESPAN_SECONDS", value = tostring(var.access_token_lifespan_seconds) }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.frontend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${local.name_prefix}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = 1024
  memory = 2048

  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.worker_task.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "penflow-worker"
      image     = "${aws_ecr_repository.worker.repository_url}:${var.worker_image_tag}"
      essential = true

      environment = [
        { name = "AWS_REGION", value = var.aws_region },
        { name = "REPORT_OUTPUT_DIR", value = "/tmp/generated_reports" },
        { name = "REPORT_STORAGE", value = "s3" },
        { name = "REPORT_S3_BUCKET", value = aws_s3_bucket.reports.bucket },
        { name = "SCAN_MODE", value = "LIVE" },
        { name = "BACKEND_URL", value = "http://penflow-backend.${var.project_name}.local:3001" },
        { name = "RABBITMQ_PROTOCOL", value = "amqps" },
        {
          name  = "RABBITMQ_HOST",
          value = replace(replace(aws_mq_broker.rabbitmq.instances[0].endpoints[0], "amqps://", ""), ":5671", "")
        },
        { name = "RABBITMQ_PORT", value = "5671" },
        { name = "RABBITMQ_USERNAME", value = var.rabbitmq_username }
      ]

      secrets = [
        { name = "RABBITMQ_PASSWORD", valueFrom = aws_secretsmanager_secret.rabbitmq_password.arn },
        { name = "HIBP_API_KEY", valueFrom = aws_secretsmanager_secret.hibp_api_key.arn },
        { name = "SHODAN_API_KEY", valueFrom = aws_secretsmanager_secret.shodan_api_key.arn },
        { name = "URLSCAN_API_KEY", valueFrom = aws_secretsmanager_secret.urlscan_api_key.arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.worker.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_task_definition" "keycloak" {
  family                   = "${local.name_prefix}-keycloak"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"

  cpu    = 1024
  memory = 2048

  execution_role_arn = aws_iam_role.ecs_execution.arn
  task_role_arn      = aws_iam_role.keycloak_task.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = "penflow-keycloak"
      image     = "${aws_ecr_repository.keycloak.repository_url}:${var.keycloak_image_tag}"
      essential = true

      command = [
        "start",
        "--import-realm"
      ]

      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
          name          = "penflow-keycloak-8080-tcp"
          appProtocol   = "http"
        }
      ]

      environment = [
        { name = "KC_DB", value = "postgres" },
        { name = "KC_DB_URL", value = "jdbc:postgresql://${aws_db_instance.main.address}:${aws_db_instance.main.port}/${var.keycloak_db_name}" },
        { name = "KC_DB_USERNAME", value = var.keycloak_db_username },
        { name = "KC_BOOTSTRAP_ADMIN_USERNAME", value = var.keycloak_bootstrap_admin_username },
        { name = "KC_PROXY_HEADERS", value = "xforwarded" },
        { name = "KC_HTTP_ENABLED", value = "true" },
        { name = "KC_HEALTH_ENABLED", value = "true" },
        { name = "KC_METRICS_ENABLED", value = "true" },
        { name = "KC_HTTP_MANAGEMENT_HEALTH_ENABLED", value = "false" },
        { name = "KC_HOSTNAME", value = "https://${var.auth_domain_name}" }
      ]

      secrets = [
        { name = "KC_DB_PASSWORD", valueFrom = aws_secretsmanager_secret.keycloak_db_password.arn },
        { name = "KC_BOOTSTRAP_ADMIN_PASSWORD", valueFrom = aws_secretsmanager_secret.keycloak_admin_password.arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.keycloak.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${local.name_prefix}-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "penflow-backend"
    container_port   = 3001
  }

  service_registries {
    registry_arn   = aws_service_discovery_service.backend.arn
    container_name = "penflow-backend"
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [
    aws_lb_listener.https
  ]
}

resource "aws_ecs_service" "frontend" {
  name            = "${local.name_prefix}-frontend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.frontend.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "penflow-frontend"
    container_port   = 3000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [
    aws_lb_listener.https
  ]
}

resource "aws_ecs_service" "keycloak" {
  name            = "${local.name_prefix}-keycloak-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.keycloak.arn
  desired_count   = var.keycloak_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.keycloak.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.keycloak.arn
    container_name   = "penflow-keycloak"
    container_port   = 8080
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [
    aws_lb_listener.https,
    aws_db_instance.main
  ]
}

resource "aws_ecs_service" "worker" {
  name            = "${local.name_prefix}-worker-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.worker.id]
    assign_public_ip = true
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [
    aws_mq_broker.rabbitmq,
    aws_ecs_service.backend
  ]
}