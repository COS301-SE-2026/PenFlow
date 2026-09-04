resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project_name}/backend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}/frontend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.project_name}/worker"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "keycloak" {
  name              = "/ecs/${var.project_name}/keycloak"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "email_worker" {
  name              = "/ecs/${var.project_name}/email-worker"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "schedule_worker" {
  name              = "/ecs/${var.project_name}/schedule-worker"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "celery_beat" {
  name              = "/ecs/${var.project_name}/celery-beat"
  retention_in_days = 14
}