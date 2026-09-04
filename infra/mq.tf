resource "aws_security_group" "rabbitmq" {
  name        = "${local.name_prefix}-rabbitmq-sg"
  description = "Allow RabbitMQ traffic from backend and workers."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "AMQPS from backend"
    from_port       = 5671
    to_port         = 5671
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }

  ingress {
    description     = "AMQPS from workers"
    from_port       = 5671
    to_port         = 5671
    protocol        = "tcp"
    security_groups = [aws_security_group.worker.id]
  }

  ingress {
    description     = "AMQPS from email workers"
    from_port       = 5671
    to_port         = 5671
    protocol        = "tcp"
    security_groups = [aws_security_group.email_worker.id]
  }

  ingress {
    description     = "AMQPS from scheduler tasks"
    from_port       = 5671
    to_port         = 5671
    protocol        = "tcp"
    security_groups = [aws_security_group.scheduler.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-rabbitmq-sg"
  }
}

resource "aws_mq_broker" "rabbitmq" {
  broker_name = "${local.name_prefix}-rabbitmq"

  engine_type    = "RabbitMQ"
  engine_version = var.rabbitmq_engine_version

  host_instance_type = "mq.m7g.medium"
  deployment_mode    = "SINGLE_INSTANCE"

  auto_minor_version_upgrade = true

  publicly_accessible = false

  subnet_ids = [
    aws_subnet.private[0].id
  ]

  security_groups = [
    aws_security_group.rabbitmq.id
  ]

  user {
    username = var.rabbitmq_username
    password = var.rabbitmq_password
  }

  logs {
    general = true
  }

  tags = {
    Name = "${local.name_prefix}-rabbitmq"
  }
}