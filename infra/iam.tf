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

    resources = concat(
    [
      aws_secretsmanager_secret.db_password.arn,
      aws_secretsmanager_secret.keycloak_db_password.arn,
      aws_secretsmanager_secret.keycloak_admin_password.arn,
      aws_secretsmanager_secret.rabbitmq_password.arn,
      aws_secretsmanager_secret.guest_scan_token_secret.arn,
      aws_secretsmanager_secret.app_database_password.arn,
      aws_secretsmanager_secret.rate_limit_storage_uri.arn,
      aws_secretsmanager_secret.rate_limit_proxy_secret.arn,
      aws_secretsmanager_secret.backend_tls.arn,

      aws_secretsmanager_secret.hibp_api_key.arn,
      aws_secretsmanager_secret.shodan_api_key.arn,
      aws_secretsmanager_secret.urlscan_api_key.arn,
      aws_secretsmanager_secret.smtp_password.arn,
      aws_secretsmanager_secret.keycloak_provisioner_client_secret.arn,
      aws_secretsmanager_secret.internal_webhook_secret.arn
    ],
    aws_secretsmanager_secret.gemini_api_key[*].arn
    )
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

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_iam_role" "ephemeral_worker_task" {
  name               = "${local.name_prefix}-ephemeral-worker-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json

  tags = {
    Name = "${local.name_prefix}-ephemeral-worker-task"
  }
}

data "aws_iam_policy_document" "worker_ecs_dispatch" {
  statement {
    sid     = "AllowRunTask"
    effect  = "Allow"
    actions = ["ecs:RunTask"]
    resources = [
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.name_prefix}-ephemeral-worker:*",
      "arn:aws:ecs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:task-definition/${local.name_prefix}-ephemeral-worker"
    ]
  }

  statement {
    sid       = "AllowDescribeTasks"
    effect    = "Allow"
    actions   = ["ecs:DescribeTasks"]
    resources = ["*"]
  }

  statement {
    sid     = "AllowPassRole"
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      aws_iam_role.worker_task.arn,
      aws_iam_role.ecs_execution.arn,
      aws_iam_role.ephemeral_worker_task.arn
    ]
  }
}

resource "aws_iam_role_policy" "worker_ecs_dispatch_policy" {
  name   = "${local.name_prefix}-worker-dispatch"
  role   = aws_iam_role.worker_task.id
  policy = data.aws_iam_policy_document.worker_ecs_dispatch.json
}

data "aws_partition" "current" {}

data "aws_iam_policy_document" "backend_bedrock" {
  statement {
    sid    = "InvokeTitanEmbeddingModel"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel"
    ]

    resources = [
      "arn:${data.aws_partition.current.partition}:bedrock:${var.bedrock_region}::foundation-model/${var.bedrock_embedding_model_id}"
    ]
  }
}

resource "aws_iam_role_policy" "backend_bedrock" {
  name   = "${local.name_prefix}-backend-bedrock"
  role   = aws_iam_role.backend_task.id
  policy = data.aws_iam_policy_document.backend_bedrock.json
}

data "aws_iam_policy_document" "backend_bedrock_generation" {
  statement {
    sid    = "InvokeGenerationModel"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel"
    ]

    resources = var.bedrock_generation_resource_arns
  }
}

resource "aws_iam_role_policy" "backend_bedrock_generation" {
  name   = "${local.name_prefix}-backend-bedrock-generation"
  role   = aws_iam_role.backend_task.id
  policy = data.aws_iam_policy_document.backend_bedrock_generation.json
}

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  tags = {
    Name = "${local.name_prefix}-github-actions-oidc"
  }
}

data "aws_iam_policy_document" "github_deploy_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type = "Federated"

      identifiers = [
        aws_iam_openid_connect_provider.github.arn
      ]
    }

    actions = [
      "sts:AssumeRoleWithWebIdentity"
    ]

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"

      values = [
        "sts.amazonaws.com"
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"

      values = [
        "repo:COS301-SE-2026/PenFlow:ref:refs/heads/main"
      ]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "${local.name_prefix}-github-deploy-role"
  assume_role_policy = data.aws_iam_policy_document.github_deploy_assume_role.json

  tags = {
    Name = "${local.name_prefix}-github-deploy-role"
  }
}

data "aws_iam_policy_document" "github_deploy" {
  statement {
    sid    = "GetEcrAuthorizationToken"
    effect = "Allow"

    actions = [
      "ecr:GetAuthorizationToken"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "PushDeploymentImages"
    effect = "Allow"

    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:CompleteLayerUpload",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]

    resources = [
      aws_ecr_repository.backend.arn,
      aws_ecr_repository.frontend.arn,
      aws_ecr_repository.worker.arn
    ]
  }

  statement {
    sid    = "ReadAndRegisterTaskDefinitions"
    effect = "Allow"

    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition"
    ]

    resources = ["*"]
  }

  statement {
    sid    = "UpdatePenFlowServices"
    effect = "Allow"

    actions = [
      "ecs:UpdateService"
    ]

    resources = [
      for service in [
        "backend",
        "indexing-worker",
        "frontend",
        "worker",
        "email-worker",
        "schedule-worker",
        "celery-beat"
      ] :
      "arn:aws:ecs:${var.aws_region}:491449495014:service/${local.name_prefix}-cluster/${local.name_prefix}-${service}-service"
    ]
  }

  statement {
    sid    = "PassEcsTaskRoles"
    effect = "Allow"

    actions = [
      "iam:PassRole"
    ]

    resources = [
      aws_iam_role.ecs_execution.arn,
      aws_iam_role.backend_task.arn,
      aws_iam_role.frontend_task.arn,
      aws_iam_role.worker_task.arn,
      aws_iam_role.email_worker_task.arn,
      aws_iam_role.ephemeral_worker_task.arn
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"

      values = [
        "ecs-tasks.amazonaws.com"
      ]
    }
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "${local.name_prefix}-github-deploy"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}

data "aws_iam_policy_document" "evidence_s3" {
  statement {
    sid     = "ListEvidenceBucket"
    effect  = "Allow"
    actions = ["s3:ListBucket"]

    resources = [
      aws_s3_bucket.evidence.arn
    ]
  }

  statement {
    sid    = "ReadWriteEvidence"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]

    resources = [
      "${aws_s3_bucket.evidence.arn}/engagements/*"
    ]
  }
}

resource "aws_iam_role_policy" "backend_evidence_s3" {
  name   = "${local.name_prefix}-backend-evidence-s3"
  role   = aws_iam_role.backend_task.id
  policy = data.aws_iam_policy_document.evidence_s3.json
}

resource "aws_iam_user" "github_ci" {
  name = "${local.name_prefix}-github-ci"

  tags = {
    Name = "${local.name_prefix}-github-ci"
  }
}

resource "aws_iam_policy" "github_ci" {
  name   = "${local.name_prefix}-github-ci"
  policy = data.aws_iam_policy_document.github_deploy.json
}

resource "aws_iam_user_policy_attachment" "github_ci" {
  user       = aws_iam_user.github_ci.name
  policy_arn = aws_iam_policy.github_ci.arn
}