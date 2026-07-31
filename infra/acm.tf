resource "aws_acm_certificate" "main" {
  domain_name = var.domain_name

  subject_alternative_names = [
    "www.${var.domain_name}",
    var.auth_domain_name,
  ]

  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${local.name_prefix}-certificate"
  }
}

resource "aws_acm_certificate_validation" "main" {
  certificate_arn = aws_acm_certificate.main.arn
}