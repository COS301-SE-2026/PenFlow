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