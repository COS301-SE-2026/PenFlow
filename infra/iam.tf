data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${local.name_prefix}-ecs-execution-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-ecs-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_base" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "ecs_execution_secrets" {
  statement {
    sid    = "ReadPenFlowSecrets"
    effect = "Allow"

    actions = [
      "secretsmanager:GetSecretValue"
    ]

    resources = [
      aws_secretsmanager_secret.db_password.arn,
      aws_secretsmanager_secret.keycloak_db_password.arn,
      aws_secretsmanager_secret.keycloak_admin_password.arn,
      aws_secretsmanager_secret.rabbitmq_password.arn,

      aws_secretsmanager_secret.hibp_api_key.arn,
      aws_secretsmanager_secret.shodan_api_key.arn,
      aws_secretsmanager_secret.urlscan_api_key.arn,
      aws_secretsmanager_secret.smtp_password.arn,
      aws_secretsmanager_secret.keycloak_provisioner_client_secret.arn
    ]
  }
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name   = "${local.name_prefix}-ecs-secrets"
  role   = aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.ecs_execution_secrets.json
}

resource "aws_iam_role" "backend_task" {
  name               = "${local.name_prefix}-backend-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-backend-task-role"
  }
}

resource "aws_iam_role" "worker_task" {
  name               = "${local.name_prefix}-worker-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-worker-task-role"
  }
}

resource "aws_iam_role" "frontend_task" {
  name               = "${local.name_prefix}-frontend-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-frontend-task-role"
  }
}

resource "aws_iam_role" "keycloak_task" {
  name               = "${local.name_prefix}-keycloak-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-keycloak-task-role"
  }
}


resource "aws_iam_role" "email_worker_task" {
  name               = "${local.name_prefix}-email-worker-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-email-worker-task-role"
  }
}

data "aws_iam_policy_document" "email_worker" {
  statement {
    sid    = "SendEmail"
    effect = "Allow"

    actions = [
      "ses:SendEmail",
      "ses:SendRawEmail"
    ]

    resources = [
      var.ses_identity_arn
    ]
  }

  statement {
    sid    = "ReadReports"
    effect = "Allow"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${aws_s3_bucket.reports.arn}/*"
    ]
  }
}

data "aws_iam_policy_document" "reports_s3" {
  statement {
    sid    = "ListReportsBucket"
    effect = "Allow"

    actions = [
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.reports.arn
    ]
  }

  statement {
    sid    = "ReadWriteReports"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]

    resources = [
      "${aws_s3_bucket.reports.arn}/*"
    ]
  }
}

resource "aws_iam_role_policy" "backend_reports_s3" {
  name   = "${local.name_prefix}-backend-reports-s3"
  role   = aws_iam_role.backend_task.id
  policy = data.aws_iam_policy_document.reports_s3.json
}

resource "aws_iam_role_policy" "worker_reports_s3" {
  name   = "${local.name_prefix}-worker-reports-s3"
  role   = aws_iam_role.worker_task.id
  policy = data.aws_iam_policy_document.reports_s3.json
}

resource "aws_iam_role_policy" "email_worker" {
  name   = "${local.name_prefix}-email-worker"
  role   = aws_iam_role.email_worker_task.id
  policy = data.aws_iam_policy_document.email_worker.json
}