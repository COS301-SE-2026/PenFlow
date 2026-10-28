resource "aws_secretsmanager_secret" "db_password" {
  name = "${local.name_prefix}/database/password"
}

resource "aws_secretsmanager_secret" "keycloak_db_password" {
  name = "${local.name_prefix}/keycloak/db-password"
}

resource "aws_secretsmanager_secret" "keycloak_admin_password" {
  name = "${local.name_prefix}/keycloak/bootstrap-admin-password"
}

resource "aws_secretsmanager_secret" "rabbitmq_password" {
  name = "${local.name_prefix}/rabbitmq/password"
}

resource "aws_secretsmanager_secret" "hibp_api_key" {
  name = "${local.name_prefix}/external-apis/hibp"
}

resource "aws_secretsmanager_secret" "shodan_api_key" {
  name = "${local.name_prefix}/external-apis/shodan"
}

resource "aws_secretsmanager_secret" "urlscan_api_key" {
  name = "${local.name_prefix}/external-apis/urlscan"
}

resource "aws_secretsmanager_secret" "smtp_password" {
  name = "${local.name_prefix}/email/smtp-password"
}

resource "aws_secretsmanager_secret" "keycloak_provisioner_client_secret" {
  name = "${local.name_prefix}/keycloak/provisioner-client-secret"
}

resource "aws_secretsmanager_secret" "guest_scan_token_secret" {
  name = "${local.name_prefix}/guest-scan-token-secret"
}

resource "aws_secretsmanager_secret_version" "guest_scan_token_secret" {
  secret_id     = aws_secretsmanager_secret.guest_scan_token_secret.id
  secret_string = var.guest_scan_token_secret
}

resource "aws_secretsmanager_secret" "app_database_password" {
  name = "${local.name_prefix}/database/runtime-password"
}

resource "aws_secretsmanager_secret_version" "app_database_password" {
  secret_id     = aws_secretsmanager_secret.app_database_password.id
  secret_string = var.app_database_password
}

resource "aws_secretsmanager_secret" "backend_tls" {
  name = "${local.name_prefix}/backend/tls"
}